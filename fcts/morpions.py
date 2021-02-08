import random
import discord
import asyncio
import time
import emoji as emojilib
from discord.ext import commands
from utils import zbot, MyContext


class Morpions(commands.Cog):

    def __init__(self, bot: zbot):
        self.bot = bot
        self.file = 'morpions'
        self.in_game = dict()


    @commands.command(name="tic-tac-toe", aliases=['morpion', 'tictactoe', 'ttt'])
    async def main(self, ctx: MyContext, leave: str = None):
        """A simple mini-game that consists of aligning three chips on a 9-square grid.
    The bot plays in red, the user in blue.
    Use 'tic-tac-toe leave' to make you leave the game if you're stuck in it.

    ..Doc miscellaneous.html#tic-tac-toe
    """
        if leave == 'leave':
            if ctx.author.id not in self.in_game.keys():
                await ctx.send(await self.bot._(ctx.channel, 'morpion', 'not-playing'))
            else:
                self.in_game.pop(ctx.author.id)
                await ctx.send(await self.bot._(ctx.channel, 'morpion', 'game-removed'))
            return
        if ctx.author.id in self.in_game.keys():
            await ctx.send(await self.bot._(ctx.channel, 'morpion', 'already-playing'))
            return
        self.in_game[ctx.author.id] = time.time()
        game = self.Game(ctx, self)
        await game.get_emojis()
        await game.start()
        self.in_game.pop(ctx.author.id, None)

    class Game():

        def __init__(self, ctx: MyContext, Cog):
            self.cog = Cog
            self.ctx = ctx
            self.bot = ctx.bot
            self.emojis = list()
            self.entrees_valides = [str(x) for x in range(1, 10)]
            self.compositions_gagnantes = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [
                0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]]

        async def get_emojis(self):
            if self.bot.current_event == 'halloween':
                self.emojis = ["🎃", ":bat:"]
            if self.bot.current_event == "christmas":
                self.emojis = ["☃️", "🎄"]
            if self.bot.current_event == 'fish':
                self.emojis = ["🐟", "🐠"]
            if self.ctx.guild:
                config = await self.bot.get_config(self.ctx.guild.id, "morpion_emojis")
                if config is not None and config != "":
                    for r in config.split(';'):
                        if r.isnumeric():
                            d_em = discord.utils.get(
                                self.bot.emojis, id=int(r))
                            if d_em is not None:
                                self.emojis.append(str(d_em))
                        else:
                            self.emojis.append(
                                emojilib.emojize(r, use_aliases=True))
                    self.emojis = self.emojis[:2]
            if len(self.emojis) < 2:
                self.emojis = [':red_circle:', ':blue_circle:']

        async def qui_commence(self) -> bool:
            """Le joueur est True, l'ordinateur est False"""
            return random.choice([True, False])

        async def afficher_grille(self, grille: list) -> str:
            """Affiche la grille qui est une liste sous forme de chaine de caractères"""
            affichage_grille = ''
            for k in range(9):
                if k % 3 == 0:
                    affichage_grille += '\n'
                if grille[k] in range(10):
                    affichage_grille += '<:{}>'.format(
                        self.bot.get_cog('Emojis').numbEmojis[grille[k]])
                elif grille[k] == 'O':
                    affichage_grille += self.emojis[0]
                else:
                    affichage_grille += self.emojis[1]
            return affichage_grille

        async def test_place_valide(self, grille: list, saisie: str):
            """Test si la place saisie par le joueur est libre"""
            return False if (str(grille[int(saisie)-1]) == 'X') or (str(grille[int(saisie)-1]) == 'O') else True

        async def remplacer_valeur(self, grille: list, tour: bool, saisie: str):
            """Remplace la valeur de celui qui joue"""
            return ['X' if x == int(saisie) else x for x in grille] if tour == True else ['O' if x == int(saisie) else x for x in grille]

        async def test_win(self, grille: list):
            """Test s'il y a une position de victoire"""
            for k in range(8):
                if grille[self.compositions_gagnantes[k][0]] == grille[self.compositions_gagnantes[k][1]] == grille[self.compositions_gagnantes[k][2]]:
                    return True
            return False

        async def test_cases_vides(self, grille: list):
            """Renvoie True s'il reste des cases vides"""
            return grille.count('O') + grille.count('X') != 9

        async def start(self):
            ctx = self.ctx
            try:
                grille = [x for x in range(1, 10)]
                tour = await self.qui_commence()
                u_begin = await self.bot._(ctx.channel, 'morpion', 'user-begin' if tour else 'bot-begin')
                await ctx.send(u_begin.format(ctx.author.mention)+await self.bot._(ctx.channel, 'morpion', 'tip', symb1=self.emojis[0], symb2=self.emojis[1]))
                match_nul = True

                def check(m):
                    return m.channel == ctx.channel and m.author == ctx.author
                display_grille = True
                while await self.test_cases_vides(grille):
                    if ctx.author.id not in self.cog.in_game.keys():
                        return
                ###
                    if tour == True:  # Si c'est au joueur
                        if display_grille:
                            await ctx.send(await self.afficher_grille(grille))
                        display_grille = True
                        try:
                            msg = await self.bot.wait_for('message', check=check, timeout=50)
                        except asyncio.TimeoutError:
                            await ctx.channel.send(await self.bot._(ctx.channel, 'morpion', 'too-late'))
                            return
                        saisie = msg.content
                        if msg.content in self.entrees_valides:
                            if await self.test_place_valide(grille, saisie) == True:
                                grille = await self.remplacer_valeur(grille, tour, saisie)
                                tour = False
                            else:
                                await ctx.send(await self.bot._(ctx.channel, 'morpion', 'pion-1'))
                                display_grille = False
                                continue
                        elif msg.content.endswith("leave"):
                            return
                        else:
                            await ctx.send(await self.bot._(ctx.channel, 'morpion', 'pion-2'))
                            display_grille = False
                            continue
                ###
                    else:  # Si c'est à l'ordinateur
                        # On met une valeur au cas ou il n'y ai pas de possibilité de gagner
                        saisie = random.randint(1, 10)
                        # Test si joueur va gagner ou si bot peut gagner
                        for k in range(1, 10):
                            for i in [True, False]:
                                grille_copie = grille
                                grille_copie = await self.remplacer_valeur(grille, i, k)
                                if await self.test_win(grille_copie) == True:
                                    saisie = k
                                    break
                        # Test si la saisie est valide
                        if str(saisie) in self.entrees_valides:
                            if await self.test_place_valide(grille, saisie) == True:
                                grille = await self.remplacer_valeur(grille, tour, saisie)
                                tour = True
                            else:
                                continue
                        else:
                            continue
                        display_grille = True
                ###
                    if await self.test_win(grille) == True:
                        match_nul = False
                        break
                ###
                if match_nul:
                    await self.bot.get_cog("Utilities").add_user_eventPoint(ctx.author.id, 1)
                    resultat = await self.bot._(ctx.channel, 'morpion', 'nul')
                else:
                    if tour:  # Le bot a gagné
                        resultat = await self.bot._(ctx.channel, 'morpion', 'win-2')
                    else:  # L'utilisateur a gagné
                        resultat = await self.bot._(ctx.channel, 'morpion', 'win-1')
                        await self.bot.get_cog("Utilities").add_user_eventPoint(ctx.author.id, 4)
                await ctx.send(await self.afficher_grille(grille)+'\n'+resultat.format(ctx.author.mention))
            except Exception as e:
                await self.bot.get_cog('Errors').on_command_error(ctx, e)


def setup(bot):
    bot.add_cog(Morpions(bot))
