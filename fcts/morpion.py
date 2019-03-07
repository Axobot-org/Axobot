import random, discord, asyncio
from discord.ext import commands

class MorpionCog:

    def __init__(self,bot):
        self.bot = bot
        self.entrees_valides = '123456789'
        self.file = 'morpion'
        self.compositions_gagnantes = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]]


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

    async def test_saisie_valide(self,saisie):
        """Test si la valeur saisie par la joueur est valide"""
        return False if str(saisie) not in self.entrees_valides else True

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

    async def resultat_final(self,tour):
        """Renvoie qui a gagné la partie"""
        return "Bien joué, {} a gagné !" if tour == False else "J'ai gagné !"

    async def test_cases_vides(self,grille):
        """Renvoie True s'il reste des cases vides"""
        return grille.count('O') +grille.count('X') != 9

    @commands.command(name="morpion")
    async def main(self,ctx):
        #Note : Le joueur est les CROIX (X) et l'ordinateur les RONDS (O)
        try:
            grille = [x for x in range(1,10)]
            tour = await self.qui_commence()
            await ctx.send(str("{}, à toi de commencer !".format(ctx.author.mention) if tour == True else "Allez hop, je commence !")+"\n*Pour jouer, il suffit de taper un nombre entre 1 et 9, correspondant à la case choisie*")
            resultat = "Match nul, personne n'a gagné..."
            def check(m):
                # return m.content in [str(x) for x in range(1,10)] and m.channel == ctx.channel and m.author==ctx.author
                return m.channel == ctx.channel and m.author==ctx.author
            while await self.test_cases_vides(grille):
            ###
                if tour == True:   #Si c'est au joueur
                    await ctx.send(await self.afficher_grille(grille))
                    try:
                        msg = await self.bot.wait_for('message', check=check,timeout=45)
                    except asyncio.TimeoutError:
                        await ctx.channel.send("Vous avez mis trop de temps à vous décider")
                        return
                    saisie = msg.content
                    if await self.test_saisie_valide(saisie) == True:
                        if await self.test_place_valide(grille,saisie) == True:
                            grille = await self.remplacer_valeur(grille,tour,saisie)
                            tour = False
                        else :
                            await ctx.send('Il y a déjà un pion sur cette case !')
                            continue
                    else :
                        await ctx.send('Case saisie invalide !')
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
                    if await self.test_saisie_valide(saisie) == True:
                        if await self.test_place_valide(grille,saisie) == True:
                            grille = await self.remplacer_valeur(grille,tour,saisie)
                            tour = True
                        else:
                            continue
                    else:
                        continue
            ###
                if await self.test_win(grille) == True:
                    resultat = await self.resultat_final(tour)
                    break
            ###
            await ctx.send(await self.afficher_grille(grille)+'\n'+resultat.format(ctx.author.mention))
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_command_error(ctx,e)

def setup(bot):
    bot.add_cog(MorpionCog(bot))