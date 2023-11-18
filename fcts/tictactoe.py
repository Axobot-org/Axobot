import asyncio
import random
import time
from typing import Literal

import discord
from discord.ext import commands

from libs.checks.checks import is_ttt_enabled
from libs.bot_classes import Axobot, MyContext
from libs.serverconfig.options_list import options


class TicTacToe(commands.Cog):
    "Allow users to play PvP tic-tac-toe"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = 'tictactoe'
        self.in_game = {}
        self.types: tuple[str] = options['ttt_display']['values']

    async def get_ttt_mode(self, ctx: MyContext) -> str:
        """Get the used mode for a specific context"""
        if ctx.guild is None:
            return options["ttt_display"]["default"]
        return await ctx.bot.get_config(ctx.guild.id, "ttt_display")

    @commands.command(name="tic-tac-toe", aliases=['morpion', 'tictactoe', 'ttt'])
    @commands.check(is_ttt_enabled)
    async def main(self, ctx: MyContext, leave: Literal['leave'] = None):
        """A simple mini-game that consists of aligning three chips on a 9-square grid.
    The bot plays in red, the user in blue.
    Use 'tic-tac-toe leave' to make you leave the game if you're stuck in it.

    ..Doc miscellaneous.html#tic-tac-toe
    """
        if leave == 'leave':
            if ctx.author.id not in self.in_game:
                await ctx.send(await self.bot._(ctx.channel, 'tictactoe.not-playing'))
            else:
                self.in_game.pop(ctx.author.id)
                await ctx.send(await self.bot._(ctx.channel, 'tictactoe.game-removed'))
            return
        if ctx.author.id in self.in_game:
            await ctx.send(await self.bot._(ctx.channel, 'tictactoe.already-playing'))
            return
        self.in_game[ctx.author.id] = time.time()
        game = self.Game(ctx, self, await self.get_ttt_mode(ctx))
        await game.init_emojis()
        await game.start()
        self.in_game.pop(ctx.author.id, None)

    class Game():
        "An actual tictactoe game running"

        def __init__(self, ctx: MyContext, cog: 'TicTacToe', mode: Literal["disabled", "short", "normal"]):
            self.cog = cog
            self.ctx = ctx
            self.bot = ctx.bot
            self.use_short = mode == "short"
            self.emojis: tuple[str, str] = tuple()
            self.entrees_valides = [str(x) for x in range(1, 10)]
            self.compositions_gagnantes = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [
                0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]]

        async def init_emojis(self):
            "Init the emojis used to play"
            if self.bot.current_event == 'halloween':
                self.emojis = ("🎃", ":bat:")
            elif self.bot.current_event == "christmas":
                self.emojis = ("☃️", "🎄")
            elif self.bot.current_event == 'fish':
                self.emojis = ("🐟", "🐠")
            elif self.ctx.guild:
                self.emojis = await self.bot.get_config(self.ctx.guild.id, "ttt_emojis")
            if len(self.emojis) < 2:
                self.emojis = (':red_circle:', ':blue_circle:')

        async def player_starts(self):
            """Retourne True si le joueur commence"""
            return random.random() < 0.5

        async def display_grid(self, grille: list) -> str:
            """Affiche la grille qui est une liste sous forme de chaine de caractères"""
            affichage_grille = ''
            if self.ctx.bot_permissions.external_emojis:
                emojis = [f'<:{x}>' for x in self.bot.emojis_manager.numbers_names]
            else:
                emojis = [chr(48+i)+chr(8419) for i in range(10)]
            for k in range(9):
                if k % 3 == 0:
                    affichage_grille += '\n'
                if grille[k] in range(10):
                    affichage_grille += emojis[grille[k]]
                elif grille[k] == 'O':
                    affichage_grille += self.emojis[0]
                else:
                    affichage_grille += self.emojis[1]
            return affichage_grille

        async def test_valid_cell(self, grille: list, saisie: str):
            """Test si la place saisie par le joueur est libre"""
            return str(grille[int(saisie)-1]) not in {'X', 'O'}

        async def replace_cell(self, grille: list, tour: bool, saisie: str):
            """Remplace la valeur de celui qui joue"""
            return ['X' if x == int(saisie) else x for x in grille] if tour else ['O' if x == int(saisie) else x for x in grille]

        async def test_win(self, grille: list):
            """Test s'il y a une position de victoire"""
            for k in range(8):
                compo_gagnante = self.compositions_gagnantes[k]
                if grille[compo_gagnante[0]] == grille[compo_gagnante[1]] == grille[compo_gagnante[2]]:
                    return True
            return False

        async def test_any_empty_cell(self, grille: list):
            "Return True if there is any empty cell"
            return grille.count('O') + grille.count('X') != 9

        async def is_empty(self, grille: list):
            "Test if the whole grid is empty"
            return all(isinstance(x, int) for x in grille)

        async def start(self):
            "Actually starts the game"
            ctx = self.ctx
            try:
                grille = list(range(1, 10))
                tour = await self.player_starts()
                u_begin = await self.bot._(ctx.channel, 'tictactoe.user-begin' if tour else 'tictactoe.bot-begin')
                tip = await self.bot._(ctx.channel, 'tictactoe.tip', symb1=self.emojis[0], symb2=self.emojis[1])
                await ctx.send(u_begin.format(ctx.author.mention) + tip)
                match_nul = True

                def check(msg: discord.Message):
                    return msg.channel == ctx.channel and msg.author == ctx.author

                display_grille = True
                last_grid = None
                while await self.test_any_empty_cell(grille):
                    if ctx.author.id not in self.cog.in_game.keys():
                        return

                ###
                    if tour:  # Si c'est au joueur
                        if display_grille:
                            # if needed, clean the messages
                            if self.use_short and last_grid:
                                await last_grid.delete()
                            last_grid = await ctx.send(await self.display_grid(grille))
                        display_grille = True
                        try:
                            msg: discord.Message = await self.bot.wait_for('message', check=check, timeout=50)
                        except asyncio.TimeoutError:
                            await ctx.channel.send(await self.bot._(ctx.channel, 'tictactoe.too-late'))
                            return
                        saisie = msg.content
                        if msg.content in self.entrees_valides:
                            if await self.test_valid_cell(grille, saisie):
                                grille = await self.replace_cell(grille, tour, saisie)
                                tour = False
                                if self.use_short:
                                    await msg.delete(delay=0.1)
                            else: # cell is not empty
                                await ctx.send(await self.bot._(ctx.channel, 'tictactoe.pion-1'))
                                display_grille = False
                                continue
                        elif msg.content.endswith("leave"): # user leaves the game
                            return
                        else: # invalid cell number
                            await ctx.send(await self.bot._(ctx.channel, 'tictactoe.pion-2'))
                            display_grille = False
                            continue
                ###
                    else:  # Si c'est à l'ordinateur
                        # On met une valeur random au cas où il n'y ai pas de possibilité de gagner
                        saisie = random.randint(1, 9)
                        # Test si joueur va gagner ou si bot peut gagner
                        for k in range(1, 10):
                            for i in [True, False]:
                                grille_copie = await self.replace_cell(grille, i, k)
                                if await self.test_win(grille_copie):
                                    saisie = k
                                    break
                        # Test si la saisie est valide
                        if str(saisie) in self.entrees_valides:
                            if await self.test_valid_cell(grille, saisie):
                                grille = await self.replace_cell(grille, tour, saisie)
                                tour = True
                            else:
                                continue
                        else:
                            continue
                        display_grille = True
                ###
                    if await self.test_win(grille):
                        match_nul = False
                        break
                ###
                # if needed, clean the messages
                if self.use_short and last_grid:
                    await last_grid.delete()
                if match_nul:
                    resultat = await self.bot._(ctx.channel, 'tictactoe.nul')
                else:
                    if tour:  # Le bot a gagné
                        resultat = await self.bot._(ctx.channel, 'tictactoe.win-bot')
                    else:  # L'utilisateur a gagné
                        resultat = await self.bot._(ctx.channel, 'tictactoe.win-user', user=ctx.author.mention)
                await ctx.send(await self.display_grid(grille)+'\n'+resultat)
                if not match_nul and not tour:
                    # give event points if user won
                    await self.cog.give_event_points(ctx.channel, ctx.author, 8)
            except Exception as err:
                self.bot.dispatch("command_error", ctx, err)

    async def give_event_points(self, channel, user: discord.User, points: int):
        "Give points to a user and check if they had unlocked a card"
        if cog := self.bot.get_cog("BotEvents"):
            if not cog.current_event:
                return
            # send win reward embed
            emb = discord.Embed(
                title=await self.bot._(channel, 'bot_events.tictactoe.reward-title'),
                description=await self.bot._(channel, 'bot_events.tictactoe.reward-desc', points=points),
                color=cog.current_event_data['color'],
            )
            emb.set_author(name=user.global_name, icon_url=user.display_avatar)
            await channel.send(embed=emb)
            # send card unlocked notif
            await cog.check_and_send_card_unlocked_notif(channel, user)
            # give points
            await cog.db_add_user_points(user.id, points)


async def setup(bot):
    await bot.add_cog(TicTacToe(bot))
