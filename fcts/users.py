import importlib
from typing import Any

import discord
from asyncache import cached
from cachetools import TTLCache
from discord import app_commands
from discord.ext import commands

from libs.arguments import args
from libs.bot_classes import Axobot, MyContext
from libs.checks import checks
from libs.enums import RankCardsFlag, UserFlag

importlib.reload(args)
importlib.reload(checks)

user_options_list = {
    "animated_card": False,
    "show_tips": True,
}

class Users(commands.Cog):
    "Commands and tools related to users specifically"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = 'users'

    async def db_get_userinfo(self, user_id: int) -> dict[str, Any] | None:
        """Get the user info from the database"""
        if not self.bot.database_online:
            return None
        query = "SELECT * FROM `users` WHERE userID=%s"
        async with self.bot.db_query(query, (user_id,), fetchone=True) as query_result:
            return query_result or None

    @cached(TTLCache(maxsize=100_000, ttl=3600))
    async def db_get_user_config(self, user_id: int, config: str):
        "Get a user config value from the database"
        if config not in user_options_list:
            raise ValueError(f"Unknown user config: {config}")
        if not self.bot.database_online:
            return user_options_list[config]
        query = f"SELECT `{config}` FROM `users` WHERE userID=%s"
        async with self.bot.db_query(query, (user_id,), astuple=True, fetchone=True) as query_result:
            if len(query_result) == 0:
                return user_options_list[config]
            return bool(query_result[0])

    async def db_edit_user_flags(self, user_id: int, flags: int):
        "Change the user flags in the database"
        if not self.bot.database_online:
            return
        query = "INSERT INTO `users` (`userID`, `user_flags`) VALUES (%(user)s, %(flags)s)\
             ON DUPLICATE KEY UPDATE `user_flags`=%(flags)s"
        async with self.bot.db_query(query, {"flags": flags, "user": user_id}):
            pass

    async def db_edit_user_rankcards(self, user_id: int, rankcards: int):
        "Change the unlocked rank cards for a user in the database"
        if not self.bot.database_online:
            return
        query = "INSERT INTO `users` (`userID`, `rankcards_unlocked`) VALUES (%(user)s, %(rankcards)s)\
             ON DUPLICATE KEY UPDATE `rankcards_unlocked`=%(rankcards)s"
        async with self.bot.db_query(query, {"rankcards": rankcards, "user": user_id}):
            pass

    async def db_edit_user_xp_card(self, user_id: int, card_style: str):
        "Change the user xp card in the database"
        if not self.bot.database_online:
            return
        query = "INSERT INTO `users` (`userID`, `xp_style`) VALUES (%(user)s, %(style)s)\
                ON DUPLICATE KEY UPDATE `xp_style`=%(style)s"
        async with self.bot.db_query(query, {"style": card_style, "user": user_id}):
            pass

    async def db_edit_user_config(self, user_id: int, config: str, value: bool):
        "Change a user config in the database"
        if config not in user_options_list:
            raise ValueError(f"Unknown user config: {config}")
        if not self.bot.database_online:
            return
        query = f"INSERT INTO `users` (`userID`, `{config}`) VALUES (%(user)s, %(value)s)\
                ON DUPLICATE KEY UPDATE `{config}`=%(value)s"
        async with self.bot.db_query(query, {"value": value, "user": user_id}):
            pass

    async def db_used_rank(self, user_id: int):
        """Write in the database that a user used its rank card"""
        if not self.bot.database_online:
            return
        query = "INSERT INTO `users` (`userID`, `used_rank`) VALUES (%s, 1) ON DUPLICATE KEY UPDATE `used_rank`=1"
        async with self.bot.db_query(query, (user_id,)):
            pass

    async def get_userflags(self, user: discord.User) -> list[str]:
        """Check what user flags has a user"""
        if not self.bot.database_online:
            return []
        if userinfo := await self.db_get_userinfo(user.id):
            return UserFlag().int_to_flags(userinfo['user_flags'])
        return []

    async def has_userflag(self, user: discord.User, flag: str) -> bool:
        """Check if a user has a specific user flag"""
        if flag not in UserFlag.FLAGS.values():
            return False
        return flag in await self.get_userflags(user)

    async def get_rankcards(self, user: discord.User) -> list[str]:
        """Check what rank cards got unlocked by a user"""
        if not self.bot.database_online:
            return []
        if userinfo := await self.db_get_userinfo(user.id):
            return RankCardsFlag().int_to_flags(userinfo['rankcards_unlocked'])
        return []

    async def has_rankcard(self, user: discord.User, rankcard: str) -> bool:
        """Check if a user has unlocked a specific rank card"""
        if rankcard not in RankCardsFlag.FLAGS.values():
            return False
        return rankcard in await self.get_rankcards(user)

    async def set_rankcard(self, user: discord.User, style: str, add: bool=True):
        """Add or remove a rank card style for a user"""
        if style not in RankCardsFlag.FLAGS.values():
            raise ValueError(f"Unknown card style: {style}")
        rankcards: list = await self.get_rankcards(user)
        if style in rankcards and add:
            return
        if style not in rankcards and not add:
            return
        if add:
            rankcards.append(style)
        else:
            rankcards.remove(style)
        await self.db_edit_user_rankcards(user.id, RankCardsFlag().flags_to_int(rankcards))

    async def get_rankcards_stats(self) -> dict:
        """Get how many users use any rank card"""
        if not self.bot.database_online:
            return {}
        try:
            query = "SELECT xp_style, Count(*) as count FROM `users` WHERE used_rank=1 GROUP BY xp_style"
            async with self.bot.db_query(query, astuple=True) as query_results:
                result = {x[0]: x[1] for x in query_results}
        except Exception as err:
            self.bot.dispatch("error", err)
            return {}
        if '' in result:
            result['default'] = result.pop('')
        return result

    async def card_style_autocomplete(self, user: discord.User, current: str):
        "Autocompletion for a card style name"
        styles_list: list[str] = await self.bot.get_cog('Utilities').allowed_card_styles(user)
        filtered = sorted(
            (not name.startswith(current), name) for name in styles_list
            if current in name
        )
        return [
            app_commands.Choice(name=value[1], value=value[1])
            for value in filtered
        ][:25]

    @commands.hybrid_group(name='profile')
    async def profile_main(self, ctx: MyContext):
        """Configure the bot for your own usage"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @profile_main.command(name='card-preview')
    @app_commands.describe(style="The name of the card style you want to preview. Leave empty for your current style")
    @commands.check(checks.database_connected)
    @commands.cooldown(3, 45, commands.BucketType.user)
    @commands.cooldown(5, 60, commands.BucketType.guild)
    async def profile_cardpreview(self, ctx: MyContext, style: args.CardStyle | None=None):
        """Get a preview of a card style

        ..Example profile card-preview

        ..Example profile card-preview red

        ..Doc user.html#change-your-xp-card"""
        if ctx.current_argument != style:
            available_cards = ', '.join(await ctx.bot.get_cog('Utilities').allowed_card_styles(ctx.author))
            await ctx.send(await self.bot._(ctx.channel, 'users.invalid-card', cards=available_cards))
            return
        if not ctx.bot_permissions.attach_files:
            await ctx.send(await self.bot._(ctx.channel, 'users.missing-attach-files'))
            return
        await ctx.defer()
        if style is None:
            style = await self.bot.get_cog('Utilities').get_xp_style(ctx.author)
        profile_card_cmd = await self.bot.get_command_mention("profile card")
        desc = await self.bot._(ctx.channel, "users.card-desc", profile_cmd=profile_card_cmd)
        xp_cog = self.bot.get_cog('Xp')
        translations_map = await xp_cog.get_card_translations_map(ctx.channel)
        card = await xp_cog.create_card(translations_map, ctx.author, style, xp=30, rank=0, ranks_nb=1,
                                                        levels_info=[1, 85, 0])
                                                        # current level, xp for next level, xp for current level
        await ctx.send(desc, file=card)

    @profile_cardpreview.autocomplete("style")
    async def cardpreview_autocomplete_style(self, inter: discord.Interaction, current: str):
        return await self.card_style_autocomplete(inter.user, current)

    @profile_main.command(name='card')
    @app_commands.describe(style="The name of the card style you want to use")
    @commands.cooldown(3, 45, commands.BucketType.user)
    @commands.check(checks.database_connected)
    async def profile_card(self, ctx: MyContext, style: args.CardStyle):
        """Change your xp card style.

        ..Example profile card christmas23

        ..Doc user.html#change-your-xp-card"""
        if style is None and len(ctx.view.buffer.split(' ')) > 2:
            # unknown style, send the whole list
            available_cards = ', '.join(await ctx.bot.get_cog('Utilities').allowed_card_styles(ctx.author))
            if ctx.view.buffer.split(' ')[2] == 'list':
                try:
                    # send the rank card notification if needed
                    await self.bot.get_cog("BotEvents").check_and_send_card_unlocked_notif(ctx.channel, ctx.author)
                    await self.bot.get_cog("BotEvents").reload_event_rankcard(ctx.author.id)
                except Exception as err:
                    self.bot.dispatch("error", err)
                await ctx.send(await self.bot._(ctx.channel, 'users.list-cards', cards=available_cards))
            else:
                await ctx.send(await self.bot._(ctx.channel, 'users.invalid-card', cards=available_cards))
            return
        await ctx.defer()
        await self.db_edit_user_xp_card(ctx.author.id, style)
        await ctx.send(await self.bot._(ctx.channel, 'users.changed-card', style=style))

    @profile_card.autocomplete("style")
    async def card_autocomplete_style(self, inter: discord.Interaction, current: str):
        return await self.card_style_autocomplete(inter.user, current)

    @profile_main.command(name='list-card-styles')
    @commands.cooldown(3, 45, commands.BucketType.user)
    @commands.check(checks.database_connected)
    async def profile_card_list(self, ctx: MyContext):
        "List the available card styles for you"
        available_cards = '\n- ' + '\n- '.join(await ctx.bot.get_cog('Utilities').allowed_card_styles(ctx.author))
        await ctx.send(await self.bot._(ctx.channel, 'users.list-cards', cards=available_cards))

    @profile_main.command(name="config")
    @commands.check(checks.database_connected)
    @app_commands.choices(option=[
        discord.app_commands.Choice(name=option, value=option)
        for option in user_options_list
    ])
    async def user_config(self, ctx: MyContext, option: str, enable: bool | None=None):
        """Modify any config option
        Here you can enable or disable one of the users option that Axobot has, which are:
        - animated_card: Display an animated rank card if your pfp is a gif (way slower rendering)
        - show_tips: Show tips when you use some specific command

        Value can only be a boolean (true/false)
        Providing empty value will show you the current value and more details"""
        if option not in user_options_list:
            await ctx.send(await self.bot._(ctx.channel, "users.config_list", options=" - ".join(user_options_list)))
            return
        if enable is None:
            value = await self.db_get_user_config(ctx.author.id, option)
            if ctx.guild is None or ctx.channel.permissions_for(ctx.guild.me).external_emojis:
                emojis = self.bot.emojis_manager.customs['green_check'], self.bot.emojis_manager.customs['red_cross']
            else:
                emojis = ('✅','❎')
            if value:
                await ctx.send(emojis[0]+" "+await self.bot._(ctx.channel, f'users.set_config.{option}.true'))
            else:
                await ctx.send(emojis[1]+" "+await self.bot._(ctx.channel, f'users.set_config.{option}.false'))
        else:
            await self.db_edit_user_config(ctx.author.id, option, enable)
            await ctx.send(await self.bot._(ctx.channel, 'users.config_success', opt=option))


async def setup(bot):
    await bot.add_cog(Users(bot))
