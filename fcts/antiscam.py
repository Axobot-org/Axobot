import copy
import typing
import discord
from discord.ext import commands
from libs.antiscam.classes import EMBED_COLORS, MsgReportView, PredictionResult
from libs.bot_classes import Zbot, MyContext
from libs.antiscam import AntiScamAgent, Message, update_unicode_map

from . import checks

def is_immune(member: discord.Member) -> bool:
    "Check if a member is immune to the anti-scam feature"
    return (member.bot
            or member.guild_permissions.administrator
            or member.guild_permissions.manage_messages
            or member.guild_permissions.manage_guild)

class AntiScam(commands.Cog):
    "Anti scam feature which read every message and detect if they are malicious"

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "antiscam"
        self.agent = AntiScamAgent()
        self.table = 'messages_beta'

    async def cog_load(self):
        "Load websites list from database"
        if self.bot.database_online:
            try:
                data: dict[str, bool] = {}
                query = "SELECT `domain`, `is_safe` FROm `spam-detection`.`websites`"
                async with self.bot.db_query(query) as query_result:
                    for row in query_result:
                        data[row['domain']] = row['is_safe']
                self.agent.save_websites_locally(data)
                self.bot.log.info(f"[antiscam] Loaded {len(data)} domain names from database")
                return
            except Exception as err:
                self.bot.dispatch("error", err, "While loading antiscam domains list")
        self.agent.fetch_websites_locally()
        self.bot.log.info(f"[antiscam] Loaded {len(self.agent.websites_list)} domain names from local file")

    @property
    def report_channel(self) -> discord.TextChannel:
        return self.bot.get_channel(913821367500148776)

    async def send_bot_log(self, msg: discord.Message, deleted: bool):
        "Send a log to the bot internal log channel"
        emb = discord.Embed(title=f"Scam message {'deleted' if deleted else 'detected'}",
                            description=msg.content,
                            color=discord.Color.red() if deleted else discord.Color.orange()
                            )
        emb.set_author(name=msg.author, icon_url=msg.author.display_avatar)
        emb.set_footer(text=f"{msg.guild.name} ({msg.guild.id})" if msg.guild else "No guild")
        await self.bot.send_embed(emb)

    async def db_insert_msg(self, msg: Message) -> int:
        "Insert a new suspicious message into the database"
        await self.bot.wait_until_ready()
        query = f"INSERT INTO `spam-detection`.`{self.table}` (message, normd_message, contains_everyone, url_score, mentions_count, max_frequency, punctuation_count, caps_percentage, avg_word_len, category) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        async with self.bot.db_query(query, (
            msg.message,
            msg.normd_message,
            msg.contains_everyone,
            msg.url_score,
            msg.mentions_count,
            msg.max_frequency,
            msg.punctuation_count,
            msg.caps_percentage,
            msg.avg_word_len,
            msg.category
        )) as query_result:
            return query_result

    async def db_delete_msg(self, msg_id: int) -> bool:
        "Delete a report message from the database"
        await self.bot.wait_until_ready()
        query = f"DELETE FROM `spam-detection`.`{self.table}` WHERE id = %s"
        async with self.bot.db_query(query, (msg_id, ), returnrowcount=True) as query_result:
            return query_result > 0

    async def db_update_msg(self, msg_id: int, new_category: str) -> bool:
        "Update a message category in the database"
        await self.bot.wait_until_ready()
        query = f"UPDATE `spam-detection`.`{self.table}` SET category = %s WHERE id = %s"
        if category_id := self.agent.get_category_id(new_category):
            async with self.bot.db_query(query, (category_id, msg_id), returnrowcount=True) as query_result:
                return query_result > 0
        return False

    async def create_embed(self, msg: Message, author: discord.User, row_id: int, status: str, predicted: PredictionResult):
        "Create an Embed object for a given message report"
        emb = discord.Embed(title="New report",
                            description=msg.message,
                            color=int(EMBED_COLORS[status][1:], 16)
                            )
        emb.set_footer(
            text=f'Sent by {author} • ID {row_id}',
            icon_url=author.avatar or None
        )
        emb.add_field(name="Status", value=status.title())
        if predicted:
            pred_title = self.agent.categories[predicted.result].title()
            pred_value = round(
                predicted.probabilities[predicted.result]*100, 2)
            emb.add_field(name="According to Zbot",
                          value=f'{pred_title} ({pred_value}%)')
        return emb

    async def send_report(self, ctx: commands.Context, row_id: int, msg: Message):
        "Send a message report into the internal reports channel"
        prediction = self.agent.predict_bot(msg)
        emb = await self.create_embed(msg, ctx.author, row_id, "pending", prediction)
        await self.report_channel.send(embed=emb, view=MsgReportView(row_id))

    async def edit_report_message(self, message: discord.InteractionMessage, new_status: str):
        "Edit a given report message to include its new status"
        emb = message.embeds[0]
        emb.set_field_at(0, name=emb.fields[0].name, value=new_status.title())
        emb.color = int(EMBED_COLORS[new_status][1:], 16)
        await message.edit(embed=emb)
        if new_status == 'deleted':
            await message.delete(delay=3)

    @commands.group(name="antiscam")
    async def antiscam(self, ctx: MyContext):
        """Everything related to the antiscam feature

        ..Doc moderator.html#anti-scam"""

    @antiscam.command(name="test")
    @commands.cooldown(5, 30, commands.BucketType.user)
    async def antiscam_test(self, ctx: MyContext, *, msg: str):
        """Test the antiscam feature with a given message

        ..Example antiscam test free nitro for everyone at bit.ly/tomato"""
        data = Message.from_raw(msg, 0, self.agent.websites_list)
        pred = self.agent.predict_bot(data)
        url_score = await self.bot._(ctx.channel, "antiscam.url-score", score=data.url_score)
        result_ = await self.bot._(ctx.channel, "antiscam.result")
        probabilities_ = await self.bot._(ctx.channel, "antiscam.probabilities")
        probas = '\n    - '.join(f'{self.agent.categories[c]}: {round(p*100, 1)}%' for c, p in pred.probabilities.items())
        msg = f"""{result_} **{self.agent.categories[pred.result]}**

{probabilities_}
    - {probas}
{url_score}"""
        await ctx.send(msg)

    @antiscam.command(name="enable")
    @commands.guild_only()
    @commands.check(checks.has_manage_guild)
    async def antiscam_enable(self, ctx: MyContext):
        """Enable the anti scam feature in your server

        ..Doc moderator.html#anti-scam"""
        msg: discord.Message = copy.copy(ctx.message)
        msg.content =  f'{ctx.prefix}config change anti_scam true'
        new_ctx = await self.bot.get_context(msg)
        await self.bot.invoke(new_ctx)

    @antiscam.command(name="disable")
    @commands.guild_only()
    @commands.check(checks.has_manage_guild)
    async def antiscam_disable(self, ctx: MyContext):
        """Disable the anti scam feature in your server

        ..Doc moderator.html#anti-scam"""
        msg: discord.Message = copy.copy(ctx.message)
        msg.content =  f'{ctx.prefix}config change anti_scam false'
        new_ctx = await self.bot.get_context(msg)
        await self.bot.invoke(new_ctx)

    @antiscam.command(name="fetch-unicode")
    @commands.check(checks.is_bot_admin)
    async def antiscam_refetch_uneicode(self, ctx: MyContext):
        "Refetch the unicode map of confusable characters"
        if not self.bot.beta:
            await ctx.send("Not usable in production!", ephemeral=True)
            return
        await update_unicode_map()
        await ctx.send("Done!")


    @antiscam.command(name="report")
    @commands.cooldown(5, 30, commands.BucketType.guild)
    @commands.cooldown(2, 10, commands.BucketType.user)
    async def antiscam_report(self, ctx: MyContext, *, message: typing.Union[discord.Message, str]):
        """Report a suspicious message to the bot team
        This will help improving the bot detection AI

        ..Doc moderator.html#anti-scam"""
        content = message.content if isinstance(message, discord.Message) else message
        mentions_count = len(message.mentions) if isinstance(message, discord.Message) else 0
        msg = Message.from_raw(content, mentions_count, self.agent.websites_list)
        if isinstance(message, discord.Message) and message.guild:
            msg.contains_everyone = f'<@&{message.guild.id}>' in content or '@everyone' in content
        else:
            msg.contains_everyone = '@everyone' in content
        msg_id = await self.db_insert_msg(msg)
        await self.send_report(ctx, msg_id, msg)
        await ctx.reply(
            await self.bot._(ctx.channel, "antiscam.report-successful"),
            allowed_mentions=discord.AllowedMentions.none()
        )

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        "Check any message for scam dangerousity"
        if (
            isinstance(msg.author, discord.User)
            or len(msg.content) < 10
            or is_immune(msg.author) or await self.bot.potential_command(msg)
        ):
            return
        await self.bot.wait_until_ready()
        if not await self.bot.get_config(msg.guild.id, "anti_scam"):
            return
        message: Message = Message.from_raw(msg.content, len(msg.mentions), self.agent.websites_list)
        if len(message.normd_message) < 3:
            return
        result = self.agent.predict_bot(message)
        if result.result > 1:
            message.category = 0
            self.bot.log.info("[antiscam] detected (%s): %s", result.probabilities[2], message.message)
            if result.probabilities[1] < 0.005: # if probability of not being harmless is less than 0.5%
                try:
                    await msg.delete() # try to delete it, silently fails
                except discord.Forbidden:
                    pass
                await self.send_bot_log(msg, deleted=True)
                self.bot.dispatch("antiscam_delete", msg, result)
                msg_id = await self.db_insert_msg(message)
                await self.send_report(msg, msg_id, message)
            elif result.probabilities[1] < 0.3:
                await self.send_bot_log(msg, deleted=False)
                self.bot.dispatch("antiscam_warn", msg, result)
                msg_id = await self.db_insert_msg(message)
                await self.send_report(msg, msg_id, message)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        "Receive interactions from an antiscam report embed and take actions based on it"
        if interaction.type != discord.InteractionType.component:
            return
        btn_id: str = interaction.data.get("custom_id", None)
        if btn_id is None or '-' not in btn_id:
            return
        try:
            action, msg_id = btn_id.split("-")
        except ValueError:
            return
        msg_id = int(msg_id)
        try:
            await interaction.response.defer()
        except (discord.NotFound, discord.HTTPException):
            # the bot already deferred it
            pass
        if action == 'delete':
            if await self.db_delete_msg(msg_id):
                await interaction.followup.send("This record has successfully been deleted", ephemeral=True)
                await self.edit_report_message(interaction.message, 'deleted')
                return
        elif action in ("harmless", "scam", "insults", "raid", "spam"):
            if await self.db_update_msg(msg_id, action):
                await interaction.followup.send(f"This record has been flagged as {action.title()}", ephemeral=True)
                await self.edit_report_message(interaction.message, action)
                return
        else:
            err = TypeError(f"Unknown antiscam button action: {action}")
            self.bot.dispatch("error", err, f"{interaction.guild_id} | {interaction.channel_id}")
            return
        await interaction.followup.send("Nothing to do", ephemeral=True)


async def setup(bot):
    await bot.add_cog(AntiScam(bot))
