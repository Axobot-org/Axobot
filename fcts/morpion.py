import random, discord, asyncio
from discord.ext import commands

class MorpionCog(commands.Cog):

    def __init__(self,bot):
        self.bot = bot
        self.entrees_valides = [str(x) for x in range(1,10)]
        self.file = 'morpion'
        self.compositions_gagnantes = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]]
        try:
            self.translate = bot.cogs['LangCog'].tr
        except:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs['LangCog'].tr


    async def qui_commence(self):
        """Le joueur est True, l'ordinateur est False"""
        return random.choice([True,False])

    async def afficher_grille(self,grille):
        """Affiche la grille qui est une liste sous forme de chaine de caractères"""
        affichage_grille = ''
        for k in range(9) :
                if k%3 == 0 :
                     affichage_grille += '\n'
                if grille[k] in range(10):
                    affichage_grille += '<:{}>'.format(self.bot.cogs['EmojiCog'].numbEmojis[grille[k]])
                elif grille[k] == 'O':
                    affichage_grille += ':red_circle:'
                else:
                    affichage_grille += ':large_blue_circle:'
        return affichage_grille

    async def test_place_valide(self,grille,saisie):
        """Test si la place saisie par le joueur est libre"""
        return False if (str(grille[int(saisie)-1]) == 'X') or (str(grille[int(saisie)-1]) == 'O') else True

    async def remplacer_valeur(self,grille,tour,saisie):
        """Remplace la valeur de celui qui joue"""
        return ['X' if x == int(saisie) else x for x in grille] if tour == True else ['O' if x == int(saisie) else x for x in grille]

    async def test_win(self,grille):
        """Test s'il y a une position de victoire"""
        for k in range(8) :
            if grille[self.compositions_gagnantes[k][0]] == grille[self.compositions_gagnantes[k][1]] == grille[self.compositions_gagnantes[k][2]] :
                return True
        return False

    async def resultat_final(self,tour,guild):
        """Renvoie qui a gagné la partie"""
        if tour:
            return await self.translate(guild,'morpion','win-2')
        return await self.translate(guild,'morpion','win-1')

    async def test_cases_vides(self,grille):
        """Renvoie True s'il reste des cases vides"""
        return grille.count('O') +grille.count('X') != 9

    @commands.command(name="crab",aliases=['morpion'])
    async def main(self,ctx):
        """A simple mini-game that consists of aligning three chips on a 9-square grid.
The bot plays in red, the user in blue.
"""
        try:
            grille = [x for x in range(1,10)]
            tour = await self.qui_commence()
            u_begin = await self.translate(ctx.guild,'morpion','user-begin') if tour == True else await self.translate(ctx.guild,'morpion','bot-begin')
            await ctx.send(u_begin.format(ctx.author.mention)+await self.translate(ctx.guild,'morpion','tip'))
            resultat = await self.translate(ctx.guild,'morpion','nul')
            def check(m):
                # return m.content in [str(x) for x in range(1,10)] and m.channel == ctx.channel and m.author==ctx.author
                return m.channel == ctx.channel and m.author==ctx.author
            display_grille = True
            while await self.test_cases_vides(grille):
            ###
                if tour == True:   #Si c'est au joueur
                    if display_grille:
                        await ctx.send(await self.afficher_grille(grille))
                    display_grille = True
                    try:
                        msg = await self.bot.wait_for('message', check=check,timeout=50)
                    except asyncio.TimeoutError:
                        await ctx.channel.send(await self.translate(ctx.guild,'morpion','too-late'))
                        return
                    saisie = msg.content
                    if msg.content in self.entrees_valides:
                        if await self.test_place_valide(grille,saisie) == True:
                            grille = await self.remplacer_valeur(grille,tour,saisie)
                            tour = False
                        else :
                            await ctx.send(await self.translate(ctx.guild,'morpion','pion-1'))
                            display_grille = False
                            continue
                    else :
                        await ctx.send(await self.translate(ctx.guild,'morpion','pion-2'))
                        display_grille = False
                        continue
            ###
                else :  #Si c'est à l'ordinateur
                    saisie = random.randint(1 , 10) #On met une valeur au cas ou il n'y ai pas de possibilité de gagner  
                    #Test si joueur va gagner ou si bot peut gagner
                    for k in range(1,10) :
                        for i in [True,False]:
                            grille_copie = grille
                            grille_copie = await self.remplacer_valeur(grille,i,k)
                            if await self.test_win(grille_copie) == True:
                                saisie = k
                                break
                    #Test si la saisie est valide
                    if str(saisie) in self.entrees_valides:
                        if await self.test_place_valide(grille,saisie) == True:
                            grille = await self.remplacer_valeur(grille,tour,saisie)
                            tour = True
                        else:
                            continue
                    else:
                        continue
                    display_grille = True
            ###
                if await self.test_win(grille) == True:
                    resultat = await self.resultat_final(tour,ctx.guild)
                    break
            ###
            await ctx.send(await self.afficher_grille(grille)+'\n'+resultat.format(ctx.author.mention))
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_command_error(ctx,e)

def setup(bot):
    bot.add_cog(MorpionCog(bot))