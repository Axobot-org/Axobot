import asyncio
import copy
import datetime
import inspect
import io
import json
import operator
import os
import sys
import textwrap
import time
import traceback
import typing
from contextlib import redirect_stdout
from glob import glob

import discord
import speedtest
from discord.ext import commands
from libs.classes import MyContext, UserFlag, Zbot, ConfirmView

from fcts import reloads


def cleanup_code(content: str):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    # remove `foo`
    return content.strip('` \n')

class Admin(commands.Cog):
    """Here are listed all commands related to the internal administration of the bot. Most of them are not accessible to users, but only to ZBot administrators."""

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "admin"
        self.emergency_time = 5.0
        if self.bot.beta:
            self.update = {'fr':'Foo','en':'Bar'}
        else:
            self.update = {'fr':None,'en':None}
        try:
            self.utilities = self.bot.get_cog("Utilities")
        except KeyError:
            pass
        self._last_result = None
        self._upvote_emojis = ()
        self.god_mode = []
    
    @property
    def upvote_emojis(self):
        if not self._upvote_emojis:
            self._upvote_emojis = (
                self.bot.get_emoji(938416027274993674),
                self.bot.get_emoji(938416007549186049)
            )
        return self._upvote_emojis

    @commands.Cog.listener()
    async def on_ready(self):
        self.utilities = self.bot.get_cog("Utilities")

    async def check_if_admin(self, ctx: MyContext):
        return await reloads.check_admin(ctx)

    async def check_if_god(self, ctx: typing.Union[discord.User, discord.Guild, MyContext]):
        "Check if a user is in God mode for a given context"
        if isinstance(ctx, discord.User):
            return await reloads.check_admin(ctx)
        elif isinstance(ctx.guild, discord.Guild) and ctx.guild is not None:
            return await reloads.check_admin(ctx) and ctx.guild.id in self.god_mode
        else:
            return await reloads.check_admin(ctx)

    async def add_success_reaction(self, msg: discord.Message):
        "Add a check reaction to a message"
        if self.bot.zombie_mode:
            return
        try:
            emoji = self.bot.get_emoji(625426328275124296)
            if emoji:
                await msg.add_reaction(emoji)
            else:
                await msg.add_reaction('\u2705')
        except discord.Forbidden:
            await msg.channel.send(":ok:")
        except discord.DiscordException:
            pass

    @commands.command(name='spoil',hidden=True)
    @commands.check(reloads.check_admin)
    async def send_spoiler(self, ctx: MyContext, *, text: str):
        """spoil spoil spoil"""
        spoil = lambda text: "||"+"||||".join(text)+"||"
        await ctx.send("```\n{}\n```".format(spoil(text)))

    @commands.command(name='msg',aliases=['tell'])
    @commands.check(reloads.check_admin)
    async def send_msg(self, ctx: MyContext, user:discord.User, *, message: str):
        """Envoie un mp à un membre"""
        try:
            await user.send(message)
            await self.add_success_reaction(ctx.message)
        except Exception as e:
            await self.bot.get_cog('Errors').on_error(e,ctx)

    @commands.group(name='admin',hidden=True)
    @commands.check(reloads.check_admin)
    async def main_msg(self, ctx: MyContext):
        """Commandes réservées aux administrateurs de ZBot"""
        if ctx.subcommand_passed is None:
            text = "Liste des commandes disponibles :"
            for cmd in sorted(ctx.command.commands, key=lambda x:x.name):
                text+="\n- {} *({})*".format(cmd.name,'...' if cmd.help is None else cmd.help.split('\n')[0])
                if isinstance(cmd, commands.core.Group):
                    for cmds in cmd.commands:
                        text+="\n        - {} *({})*".format(cmds.name,cmds.help.split('\n')[0])
            await ctx.send(text)

    @main_msg.command(name='god')
    @commands.check(reloads.check_admin)
    @commands.guild_only()
    async def enable_god_mode(self, ctx: MyContext, enable:bool=True):
        """Donne les pleins-pouvoirs aux admins du bot sur ce serveur (accès à toutes les commandes de modération)"""
        if enable:
            if ctx.guild.id not in self.god_mode:
                self.god_mode.append(ctx.guild.id)
                await ctx.send("<:nitro:548569774435598346> Mode superadmin activé sur ce serveur",delete_after=3)
            else:
                await ctx.send("Mode superadmin déjà activé sur ce serveur",delete_after=3)
        else:
            if ctx.guild.id in self.god_mode:
                self.god_mode.remove(ctx.guild.id)
                await ctx.send("Mode superadmin désactivé sur ce serveur",delete_after=3)
            else:
                await ctx.send("Ce mode n'est pas actif ici",delete_after=3)
        try:
            await ctx.message.delete()
        except:
            pass

    @main_msg.command(name="faq",hidden=True)
    @commands.check(reloads.check_admin)
    async def send_faq(self, ctx: MyContext):
        """Envoie les messages du salon <#541228784456695818> vers le salon <#508028818154323980>"""
        msg = await ctx.send("Suppression des salons...")
        destination_fr = ctx.guild.get_channel(508028818154323980)
        destination_en = ctx.guild.get_channel(541599345972346881)
        chan_fr = ctx.guild.get_channel(541228784456695818)
        chan_en = ctx.guild.get_channel(541599226623426590)
        role_fr = ctx.guild.get_role(541224634087899146)
        role_en = ctx.guild.get_role(537597687801839617)
        await destination_fr.set_permissions(role_fr, read_messages=False)
        await destination_en.set_permissions(role_en, read_messages=False)
        await destination_fr.purge()
        await destination_en.purge()
        await msg.edit(content="Envoi des messages...")
        async for message in chan_fr.history(limit=200,oldest_first=True):
            await destination_fr.send(message.content)
        async for message in chan_en.history(limit=200,oldest_first=True):
            await destination_en.send(message.content)
        await destination_fr.set_permissions(role_fr, read_messages=True)
        await destination_en.set_permissions(role_en, read_messages=True)
        await msg.edit(content="Terminé !")
        await self.add_success_reaction(ctx.message)


    @main_msg.command(name="update",hidden=True)
    @commands.check(reloads.check_admin)
    async def update_config(self, ctx: MyContext, send: str=None):
        """Préparer/lancer un message de mise à jour
        Ajouter 'send' en argument déclenche la procédure pour l'envoyer à tous les serveurs"""
        if send == 'send':
            await self.send_updates(ctx)
            return
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        msg = None
        for x in self.update.keys():
            await ctx.send("Message en {} ?".format(x))
            try:
                msg = await ctx.bot.wait_for('message', check=check,timeout=60)
            except asyncio.TimeoutError:
                return await ctx.send('Trop tard !')
            if msg.content.lower() in ['none','annuler','stop','oups']:
                return await ctx.send('Annulé !')
            self.update[x] = msg.content
        if msg:
            await self.add_success_reaction(msg)

    async def send_updates(self, ctx:MyContext):
        """Lance un message de mise à jour"""
        if self.bot.zombie_mode:
            return
        if None in self.update.values():
            return await ctx.send("Les textes ne sont pas complets !")
        text = "Vos messages contiennent"
        confirm_view = ConfirmView(
            self.bot, ctx.channel,
            validation=lambda inter: inter.user == ctx.author,
            ephemeral=False)
        await confirm_view.init()
        if max([len(x) for x in self.update.values()]) > 1900//len(self.update.keys()):
            for lang, value in self.update.items():
                text += f"\n{lang}:```\n{value}\n```"
                await ctx.send(text, view=confirm_view)
                text = ''
        else:
            text += "\n"+"\n".join([f"{lang}:\n```\n{value}\n```" for lang, value in self.update.items()])
            await ctx.send(text, view=confirm_view)

        await confirm_view.wait()
        if confirm_view.value is None:
            await ctx.send("Trop long !")
            return
        if not confirm_view.value:
            return
        count = 0
        for guild in ctx.bot.guilds:
            channels = await ctx.bot.get_config(guild.id,'bot_news')
            if channels is None or len(channels) == 0:
                continue
            channels = [guild.get_channel(int(x)) for x in channels.split(';') if len(x)>5 and x.isnumeric()]
            lang = await ctx.bot.get_config(guild.id,'language')
            if not isinstance(lang, int):
                lang = 0
            lang = ctx.bot.get_cog('Languages').languages[lang]
            if lang not in self.update.keys():
                lang = 'en'
            mentions_str = await self.bot.get_config(guild.id,'update_mentions')
            if mentions_str is None:
                mentions = []
            else:
                mentions = []
                for r in mentions_str.split(';'):
                    try:
                        mentions.append(guild.get_role(int(r)))
                    except:
                        pass
                mentions = [x.mention for x in mentions if x is not None]
            for chan in channels:
                if chan is None:
                    continue
                try:
                    await chan.send(self.update[lang]+"\n\n"+" ".join(mentions), allowed_mentions=discord.AllowedMentions(everyone=False, roles=True))
                except Exception as e:
                    await ctx.bot.get_cog('Errors').on_error(e,ctx)
                else:
                    count += 1
            if guild.id == 356067272730607628:
                fr_chan = guild.get_channel(494870602146906113)
                if fr_chan not in channels:
                    await fr_chan.send(self.update['fr']+"\n\n"+" ".join(mentions), allowed_mentions=discord.AllowedMentions(everyone=False, roles=True))
                    count += 1

        await ctx.send("Message envoyé dans {} salons !".format(count))
        # add changelog in the database
        version = self.bot.get_cog('Info').bot_version
        query = "INSERT INTO `changelogs` (`version`, `release_date`, `fr`, `en`, `beta`) VALUES (%(v)s, %(r)s, %(fr)s, %(en)s, %(b)s) ON DUPLICATE KEY UPDATE `fr` = '%(fr)s', `en` = '%(en)s';"
        args = { 'v': version, 'r': ctx.message.created_at, 'fr': self.update['fr'], 'en': self.update['en'], 'b': self.bot.beta }
        async with self.bot.db_query(query, args):
            pass
        for k in self.update.keys():
            self.update[k] = None


    @main_msg.command(name="cogs",hidden=True)
    @commands.check(reloads.check_admin)
    async def cogs_list(self, ctx: MyContext):
        """Voir la liste de tout les cogs"""
        text = str()
        for k,v in self.bot.cogs.items():
            text +="- {} ({}) \n".format(v.file,k)
        await ctx.send(text)

    @main_msg.command(name="lang-sort",hidden=True)
    @commands.check(reloads.check_admin)
    async def resort_langs(self, ctx:MyContext, *, lang:str=None):
        """Trie par ordre alphabétique les fichiers de traduction"""
        all_files = sorted([x.replace('fcts/lang/','').replace('.json','') for x in glob("fcts/lang/*.json", recursive=False)])
        if isinstance(lang,str) and ' ' in lang:
            langs = lang.split(' ')
        elif lang is None:
            langs = all_files
        elif lang in all_files:
            langs = [lang]
        else:
            return await ctx.send('Langue invalide. Liste des langues actuelles : '+" - ".join(all_files))
        output = 0
        for l in langs:
            with open(f'fcts/lang/{l}.json','r') as f:
                temp = json.load(f)
            with open(f'fcts/lang/{l}.json','w') as f:
                json.dump(temp, f,  ensure_ascii=False, indent=4, sort_keys=True)
            output += 1
        await ctx.send('{o} fichier{s} trié{s}'.format(o=output,s='' if output<2 else 's'))

    @main_msg.command(name="guilds",aliases=['servers'],hidden=True)
    @commands.check(reloads.check_admin)
    async def send_guilds_list(self, ctx: MyContext):
        """Obtenir la liste de tout les serveurs"""
        text = str()
        for x in sorted(ctx.bot.guilds, key=operator.attrgetter('me.joined_at')):
            text += "- {} (`{}` - {} membres)\n".format(x.name,x.owner,len(x.members))
            if len(text) > 1900:
                await ctx.send(text)
                text = ""
        if len(text) > 0:
            await ctx.send(text)

    @main_msg.command(name='shutdown')
    @commands.check(reloads.check_admin)
    async def shutdown(self, ctx: MyContext):
        """Eteint le bot"""
        msg = await ctx.send("Nettoyage de l'espace de travail...")
        await self.cleanup_workspace()
        await msg.edit(content="Bot en voie d'extinction")
        await self.bot.change_presence(status=discord.Status('offline'))
        self.bot.log.info("Fermeture du bot")
        await self.bot.close()

    async def cleanup_workspace(self):
        "Delete python cache files and close database connexions"
        for folder_name, _, filenames in os.walk('.'):
            for filename in filenames:
                if filename.endswith('.pyc'):
                    os.unlink(folder_name+'/'+filename)
            if  folder_name.endswith('__pycache__'):
                os.rmdir(folder_name)
        if self.bot.database_online:
            self.bot.close_database_cnx()

    @main_msg.command(name='reboot')
    @commands.check(reloads.check_admin)
    async def restart_bot(self, ctx: MyContext):
        """Relance le bot"""
        await ctx.send(content="Redémarrage en cours...")
        await self.cleanup_workspace()
        args = sys.argv
        if len(args) == 1:
            ID = self.bot.user.id
            args.append('1' if ID==486896267788812288 else '2' if ID==436835675304755200 else '3')
            args.append('n' if ctx.bot.get_cog('Events').loop.get_task() is None else 'o')
            args.append('o' if ctx.bot.rss_enabled else 'n')
        self.bot.log.info("Redémarrage du bot")
        os.execl(sys.executable, sys.executable, *args)

    @main_msg.command(name='reload')
    @commands.check(reloads.check_admin)
    async def reload_cog(self, ctx: MyContext, *, cog: str):
        """Recharge un module"""
        cogs = cog.split(" ")
        await self.bot.get_cog("Reloads").reload_cogs(ctx,cogs)
        
    @main_msg.command(name="check_tr")
    @commands.check(reloads.check_admin)
    async def check_tr(self, ctx: MyContext,lang='en',origin="fr"):
        """Vérifie si un fichier de langue est complet"""
        await self.bot.get_cog("Languages").check_tr(ctx.channel,lang,origin)

    @main_msg.command(name="membercounter")
    @commands.check(reloads.check_admin)
    async def membercounter(self, ctx: MyContext):
        """Recharge tout ces salons qui contiennent le nombre de membres, pour tout les serveurs"""
        if self.bot.database_online:
            i = 0
            for x in self.bot.guilds:
                if await self.bot.get_cog("Servers").update_memberChannel(x):
                    i += 1
            await ctx.send(f"{i} salons mis à jours !")
        else:
            await ctx.send("Impossible de faire ceci, la base de donnée est inaccessible")

    @main_msg.command(name="get_invites",aliases=['invite'])
    @commands.check(reloads.check_admin)
    async def adm_invites(self, ctx: MyContext, *, server: typing.Optional[discord.Guild]):
        """Cherche une invitation pour un serveur"""
        await ctx.author.send(await self.search_invite(server))
        await ctx.message.delete(delay=0)

    async def search_invite(self, guild: typing.Optional[discord.Guild]) -> str:
        if guild is None:
            return "Le serveur n'a pas été trouvé"
        try:
            inv = await guild.invites()
            if len(inv) > 0:
                msg = "`{}` - {} ({} membres) ".format(guild.name,inv[0],len(guild.members))
            else:
                msg = "`{}` - Le serveur ne possède pas d'invitation".format(guild.name)
        except discord.Forbidden:
            msg = "`{}` - Impossible de récupérer l'invitation du serveur (Forbidden)".format(guild.name)
        except Exception as e:
            msg = "`ERROR:` "+str(e)
            await self.bot.get_cog('Errors').on_error(e,None)
        return msg

    @main_msg.command(name="config")
    @commands.check(reloads.check_admin)
    async def admin_sconfig_see(self, ctx: MyContext, guild: discord.Guild, option=None):
        """Affiche les options d'un serveur"""
        if not ctx.bot.database_online:
            await ctx.send("Impossible d'afficher cette commande, la base de donnée est hors ligne :confused:")
            return
        try:
            await self.bot.get_cog("Servers").send_see(guild,ctx.channel,option,ctx.message,guild)
        except Exception as e:
            await self.bot.get_cog("Errors").on_command_error(ctx,e)
        else:
            await ctx.send("Serveur introuvable")

    @main_msg.command(name='db_reload')
    @commands.check(reloads.check_admin)
    async def db_reload(self, ctx: MyContext):
        """Reconnecte le bot à la base de donnée"""
        try:
            self.bot.cnx_frm.close()
            self.bot.connect_database_frm()
            self.bot.cnx_xp.close()
            self.bot.connect_database_xp()
            self.bot.cnx_stats.close()
            self.bot.connect_database_stats()
            if self.bot.cnx_frm is not None and self.bot.cnx_xp is not None and self.bot.cnx_stats is not None:
                await ctx.message.add_reaction('✅')
                if xp := self.bot.get_cog("Xp"):
                    await xp.reload_sus()
        except Exception as err:
            await self.bot.get_cog('Errors').on_command_error(ctx,err)

    @main_msg.command(name="emergency")
    @commands.check(reloads.check_admin)
    async def emergency_cmd(self, ctx: MyContext):
        """Déclenche la procédure d'urgence
        A N'UTILISER QU'EN CAS DE BESOIN ABSOLU ! Le bot quittera tout les serveurs après avoir envoyé un mp à chaque propriétaire"""
        await ctx.send(await self.emergency())

    async def emergency(self, level=100):
        if self.bot.zombie_mode:
            return
        time = round(self.emergency_time - level/100,1)
        for x in reloads.admins_id:
            try:
                user = self.bot.get_user(x)
                if user.dm_channel is None:
                    await user.create_dm()
                msg = await user.dm_channel.send("{} La procédure d'urgence vient d'être activée. Si vous souhaitez l'annuler, veuillez cliquer sur la réaction ci-dessous dans les {} secondes qui suivent l'envoi de ce message.".format(self.bot.get_cog('Emojis').customs['red_warning'],time))
                await msg.add_reaction('🛑')
            except Exception as e:
                await self.bot.get_cog('Errors').on_error(e,None)

        def check(reaction, user):
            return user.id in reloads.admins_id
        try:
            await self.bot.wait_for('reaction_add', timeout=time, check=check)
        except asyncio.TimeoutError:
            owners = list()
            servers = 0
            for server in self.bot.guilds:
                if server.id==500648624204808193:
                    continue
                try:
                    if server.owner not in owners:
                        await server.owner.send(await self.bot._(server,"admin.emergency"))
                        owners.append(server.owner)
                    await server.leave()
                    servers +=1
                except:
                    continue
            chan = await self.bot.get_channel(500674177548812306)
            await chan.send("{} Prodédure d'urgence déclenchée : {} serveurs quittés - {} propriétaires prévenus".format(self.bot.get_cog('Emojis').customs['red_alert'],servers,len(owners)))
            return "{}  {} propriétaires de serveurs ont été prévenu ({} serveurs)".format(self.bot.get_cog('Emojis').customs['red_alert'],len(owners),servers)
        for x in reloads.admins_id:
            try:
                user = self.bot.get_user(x)
                await user.send("La procédure a été annulée !")
            except Exception as e:
                await self.bot.get_cog('Errors').on_error(e,None)
        return "Qui a appuyé sur le bouton rouge ? :thinking:"

    @main_msg.command(name="code")
    @commands.check(reloads.check_admin)
    async def show_code(self, ctx: MyContext, cmd: str):
        obj = self.bot.get_command(cmd)
        if obj is not None:
            code = inspect.getsource(obj.callback)
            if len(code) > 1950:
                liste = str()
                for line in code.split('\n'):
                    if len(liste+"\n"+line) > 1950:
                        await ctx.send("```py\n{}\n```".format(liste))
                        liste = str()
                    liste += '\n'+line
            else:
                await ctx.send("```py\n{}\n```".format(code))
        else:
            await ctx.send("Commande `{}` introuvable".format(cmd))

    @main_msg.command(name="ignore")
    @commands.check(reloads.check_admin)
    async def add_ignoring(self, ctx: MyContext, ID:int):
        """Ajoute un serveur ou un utilisateur dans la liste des utilisateurs/serveurs ignorés"""
        serv = ctx.bot.get_guild(ID)
        try:
            usr = await ctx.bot.fetch_user(ID)
        except:
            usr = None
        scog = ctx.bot.get_cog('Servers')
        try:
            config = await ctx.bot.get_cog('Utilities').get_bot_infos()
            if serv is not None and usr is not None:
                await ctx.send("Serveur trouvé : {}\nUtilisateur trouvé : {}".format(serv.name,usr))
            elif serv is not None:
                servs = config['banned_guilds'].split(';')
                if str(serv.id) in servs:
                    servs.remove(str(serv.id))
                    await scog.edit_bot_infos(self.bot.user.id,[('banned_guilds',';'.join(servs))])
                    await ctx.send("Le serveur {} n'est plus blacklisté".format(serv.name))
                else:
                    servs.append(str(serv.id))
                    await scog.edit_bot_infos(self.bot.user.id,[('banned_guilds',';'.join(servs))])
                    await ctx.send("Le serveur {} a bien été blacklist".format(serv.name))
            elif usr is not None:
                usrs = config['banned_users'].split(';')
                if str(usr.id) in usrs:
                    usrs.remove(str(usr.id))
                    await scog.edit_bot_infos(self.bot.user.id,[('banned_users',';'.join(usrs))])
                    await ctx.send("L'utilisateur {} n'est plus blacklisté".format(usr))
                else:
                    usrs.append(str(usr.id))
                    await scog.edit_bot_infos(self.bot.user.id,[('banned_users',';'.join(usrs))])
                    await ctx.send("L'utilisateur {} a bien été blacklist".format(usr))
            else:
                await ctx.send("Impossible de trouver cet utilisateur/ce serveur")
            ctx.bot.get_cog('Utilities').config = None
        except Exception as e:
            await ctx.bot.get_cog('Errors').on_command_error(ctx,e)

    @main_msg.command(name="logs")
    @commands.check(reloads.check_admin)
    async def show_last_logs(self, ctx: MyContext, lines:typing.Optional[int]=15, *, match=''):
        """Affiche les <lines> derniers logs ayant <match> dedans"""
        try:
            if lines > 1000:
                match = str(lines)
                lines = 15
            with open('debug.log','r',encoding='utf-8') as file:
                text = file.read().split("\n")
            msg = str()
            liste = list()
            i = 1
            while len(liste)<lines and i<min(2000,len(text)):
                i+=1
                if (not match in text[-i]) or ctx.message.content in text[-i]:
                    continue
                liste.append(text[-i].replace('`',''))
            for i in liste:
                if len(msg+i) > 1900:
                    await ctx.send("```css\n{}\n```".format(msg))
                    msg = ""
                if len(i)<1900:
                    msg += "\n"+i.replace('`','')
            await ctx.send("```css\n{}\n```".format(msg))
        except Exception as e:
            await self.bot.get_cog('Errors').on_error(e,ctx)

    @main_msg.command(name="enable_module")
    @commands.check(reloads.check_admin)
    async def enable_module(self, ctx: MyContext, module: str, enabling: bool=True):
        """Active ou désactive un module (xp/rss/alerts)
Cette option affecte tous les serveurs"""
        if module=='xp':
            self.bot.xp_enabled = enabling
            if enabling:
                await ctx.send("L'xp est mainenant activée")
            else:
                await ctx.send("L'xp est mainenant désactivée")
        elif module=='rss':
            self.bot.rss_enabled = enabling
            if enabling:
                await ctx.send("Les flux RSS sont mainenant activée")
            else:
                await ctx.send("Les flux RSS sont mainenant désactivée")
        elif module == 'alerts':
            self.bot.alerts_enabled = enabling
            if enabling:
                await ctx.send("Le système d'alertes est mainenant activé")
            else:
                await ctx.send("Le système d'alertes est mainenant désactivé")
        else:
            await ctx.send('Module introuvable')
    
    @main_msg.command(name="flag")
    @commands.check(reloads.check_admin)
    async def admin_flag(self, ctx:MyContext, add:str, flag:str, users:commands.Greedy[discord.User]):
        """Ajoute ou retire un attribut à un utilisateur
        
        Flag valides : support, premium, contributor, partner"""
        if add not in ['add', 'remove']:
            return await ctx.send("Action invalide")
        for user in users:
            if flag not in UserFlag.FLAGS.values():
                await ctx.send("Flag invalide")
                return
            userflags: list = await self.bot.get_cog("Users").get_userflags(user)
            if userflags:
                if flag in userflags and add == 'add':
                    await ctx.send(f"L'utilisateur {user} a déjà ce flag")
                    return
                if flag not in userflags and add == 'remove':
                    return await ctx.send(f"L'utilisateur {user} n'a pas ce flag")
            if add == "add":
                userflags.append(flag)
            else:
                userflags.remove(flag)
            await self.bot.get_cog('Utilities').change_db_userinfo(user.id, 'user_flags', UserFlag().flagsToInt(userflags))
            if add == "add":
                await ctx.send(f"L'utilisateur {user} a maintenant le flag `{flag}`",delete_after=3.0)
            elif add == "remove":
                await ctx.send(f"L'utilisateur {user} n'a plus le flag `{flag}`",delete_after=3.0)
            try:
                await ctx.message.detele()
            except:
                pass

    @main_msg.command(name="loop_restart")
    @commands.check(reloads.check_admin)
    async def loop_restart(self, ctx:MyContext):
        """Relance la boucle principale"""
        try:
            ctx.bot.get_cog("Events").loop.start()
        except RuntimeError:
            await ctx.send("La boucle est déjà lancée :wink:")


    @main_msg.group(name="server")
    @commands.check(reloads.check_admin)
    async def main_botserv(self, ctx: MyContext):
        """Quelques commandes liées au serveur officiel"""
        if ctx.invoked_subcommand is None or ctx.invoked_subcommand==self.main_botserv:
            text = "Liste des commandes disponibles :"
            for cmd in ctx.command.commands:
                text+="\n- {} *({})*".format(cmd.name,cmd.help)
            await ctx.send(text)

    @main_botserv.command(name="owner_reload")
    @commands.check(reloads.check_admin)
    async def owner_reload(self, ctx: MyContext):
        """Ajoute le rôle Owner à tout les membres possédant un serveur avec le bot
        Il est nécessaire d'avoir au moins 10 membres pour que le rôle soit ajouté"""
        server = self.bot.get_guild(356067272730607628)
        if server is None:
            await ctx.send("Serveur ZBot introuvable")
            return
        role = server.get_role(486905171738361876)
        if role is None:
            await ctx.send("Rôle Owners introuvable")
            return
        owner_list = list()
        for guild in self.bot.guilds:
            if len(guild.members)>9:
                if guild.owner_id is None:
                    await ctx.send("Oops, askip le propriétaire de {} n'existe pas ._.".format(guild.id))
                    continue
                owner_list.append(guild.owner_id)
        for member in server.members:
            if member.id in owner_list and role not in member.roles:
                await ctx.send("Rôle ajouté à "+str(member))
                await member.add_roles(role,reason="This user support me")
            elif (member.id not in owner_list) and role in member.roles:
                await ctx.send("Rôle supprimé à "+str(member))
                await member.remove_roles(role,reason="This user doesn't support me anymore")
        await self.add_success_reaction(ctx.message)

    async def _get_ideas_list(self, channel: discord.TextChannel) -> list[tuple[int, datetime.timedelta, str, int, int]]:
        "Get ideas from the ideas channel"
        now = self.bot.utcnow()
        liste = list()
        async for msg in channel.history(limit=500):
            if len(msg.reactions) > 0:
                upvotes = 0
                downvotes = 0
                for reaction in msg.reactions:
                    users = [x for x in await x.users().flatten() if not x.bot]
                    if reaction.emoji in ('👍', self.upvote_emojis[0]):
                        upvotes = len(users)
                    if reaction.emoji in ('👎', self.upvote_emojis[1]):
                        downvotes = len(users)
                duration = now-msg.created_at
                if len(msg.embeds) > 0:
                    liste.append((upvotes-downvotes,duration,msg.embeds[0].fields[0].value,upvotes,downvotes))
                else:
                    liste.append((upvotes-downvotes,duration,msg.content,upvotes,downvotes))
        liste.sort(reverse=True)
        return liste

    @main_botserv.command(name="best_ideas")
    @commands.check(reloads.check_admin)
    async def best_ideas(self, ctx: MyContext, number:int=10):
        """Donne la liste des 10 meilleures idées"""
        bot_msg = await ctx.send("Chargement des idées...")
        server = self.bot.get_guild(356067272730607628)
        if server is None:
            return await ctx.send("Serveur introuvable")
        channel = server.get_channel(488769306524385301)
        if channel is None:
            return await ctx.send("Salon introuvable")
        liste = await self._get_ideas_list(channel)
        count = len(liste)
        liste = liste[:number]
        title = "Liste des {} meilleures idées (sur {}) :".format(len(liste),count)
        text = str()
        if ctx.guild is not None:
            color = ctx.guild.me.color
        else:
            color = discord.Colour(8311585)
        for reaction in liste:
            text += "\n**[{} - {}]**  {} ".format(reaction[3],reaction[4],reaction[2])
        try:
            if ctx.can_send_embed:
                emb = discord.Embed(title=title, description=text, color=color, timestamp=self.bot.utcnow())
                return await bot_msg.edit(content=None,embed=emb)
            await bot_msg.edit(content=title+text)
        except discord.HTTPException:
            await ctx.send("Le message est trop long pour être envoyé !")

    @main_msg.command(name="activity")
    @commands.check(reloads.check_admin)
    async def change_activity(self, ctx: MyContext, Type: str, * act: str):
        """Change l'activité du bot (play, watch, listen, stream)"""
        act = " ".join(act)
        if Type in ['game','play','playing']:
            await self.bot.change_presence(activity=discord.Game(name=act))
        elif Type in ['watch','see','watching']:
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,name=act,timestamps={'start':time.time()}))
        elif Type in ['listen','listening']:
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,name=act,timestamps={'start':time.time()}))
        elif Type in ['stream']:
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.streaming,name=act,timestamps={'start':time.time()}))
        else:
            await ctx.send("Sélectionnez *play*, *watch*, *listen* ou *stream* suivi du nom")
        await ctx.message.delete()

    @main_msg.command(name="speedtest")
    @commands.check(reloads.check_admin)
    async def speedtest(self, ctx: MyContext, method: str=None):
        """Fais un speedtest du vps
        Les méthodes possibles sont: dict, json, csv"""
        if method is not None and (not hasattr(speedtest.SpeedtestResults, method)):
            await ctx.send("Méthode invalide")
            return
        msg = await ctx.send("Début de l'analyse...")
        s = speedtest.Speedtest()
        s.get_servers([])
        s.get_best_server()
        s.download()
        s.upload(pre_allocate=False)
        if method is None:
            s.results.share()
        if method is None:
            result = s.results.dict()
            await msg.edit(content=f"{result['server']['sponsor']} - ping {result['server']['latency']}ms\n{result['share']}")
        elif method == "json":
            result = s.results.json(pretty=True)
            # j = json.dumps(result, indent=2)[1:-1].replace('\\"','"')
            await msg.edit(content=f"```json\n{result}\n```")
        elif method == "dict":
            result = s.results.dict()
            await msg.edit(content=f"```py\n{result}\n```")
        else:
            result = getattr(s.results, method)()
            await msg.edit(content=str(result))


    @commands.command(name='eval')
    @commands.check(reloads.check_admin)
    async def _eval(self, ctx: MyContext, *, body: str):
        """Evaluates a code
        Credits: Rapptz (https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/admin.py)"""
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
        }
        env.update(globals())

        body = cleanup_code(body)
        stdout = io.StringIO()
        try:
            to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'
        except Exception as e:
            await self.bot.get_cog('Errors').on_error(e,ctx)
            return
        try:
            exec(to_compile, env) # pylint: disable=exec-used
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()[:1990]}\n```')
        else:
            value = stdout.getvalue()
            await self.add_success_reaction(ctx.message)

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')

    @commands.command(name='execute',hidden=True)
    @commands.check(reloads.check_admin)
    async def sudo(self, ctx: MyContext, who: typing.Union[discord.Member, discord.User], *, command: str):
        """Run a command as another user
        Credits: Rapptz (https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/admin.py)"""
        msg = copy.copy(ctx.message)
        msg.author = who
        msg.content = ctx.prefix + command
        new_ctx = await self.bot.get_context(msg)
        await self.bot.invoke(new_ctx)
        await self.add_success_reaction(ctx.message)

    @commands.group(name='bug',hidden=True)
    @commands.check(reloads.check_admin)
    async def main_bug(self, ctx: MyContext):
        """Gère la liste des bugs"""

    @main_bug.command(name='add')
    async def bug_add(self, ctx: MyContext,* ,bug: str):
        """Ajoute un bug à la liste"""
        channel = ctx.bot.get_channel(929864644678549534) if self.bot.beta else ctx.bot.get_channel(488769283673948175)
        if channel is None:
            return await ctx.send("Salon 488769283673948175 introuvable")
        text = bug.split('\n')
        fr_text, en_text = text[0].replace('\\n','\n'), text[1].replace('\\n','\n')
        emb = discord.Embed(title="New bug", timestamp=self.bot.utcnow(), color=13632027)
        emb.add_field(name='Français', value=fr_text, inline=False)
        emb.add_field(name='English', value=en_text, inline=False)
        await channel.send(embed=emb)
        await self.add_success_reaction(ctx.message)

    @main_bug.command(name='fix')
    async def bug_fix(self, ctx: MyContext, msg_id: int, fixed:bool=True):
        """Marque un bug comme étant fixé"""
        chan = ctx.bot.get_channel(929864644678549534) if self.bot.beta else ctx.bot.get_channel(488769283673948175)
        if chan is None:
            return await ctx.send("Salon introuvable")
        try: # try to fetch message from the bugs channel
            msg = await chan.fetch_message(msg_id)
        except discord.DiscordException as err:
            return await ctx.send(f"`Error:` {err}")
        if len(msg.embeds) != 1:
            return await ctx.send("Nombre d'embeds invalide")
        emb = msg.embeds[0]
        if fixed: # if the bug should be marked as fixed
            emb.color = discord.Color(10146593)
            emb.title = "New bug [fixed soon]"
        else:
            emb.color = discord.Color(13632027)
            emb.title = "New bug"
        await msg.edit(embed=emb)
        await self.add_success_reaction(ctx.message)

    @commands.group(name="idea",hidden=True)
    @commands.check(reloads.check_admin)
    async def main_idea(self, ctx: MyContext):
        """Ajouter une idée dans le salon des idées, en français et anglais"""

    @main_idea.command(name='add')
    async def idea_add(self, ctx: MyContext, *, text: str):
        """Ajoute une idée à la liste"""
        channel = ctx.bot.get_channel(929864644678549534) if self.bot.beta else ctx.bot.get_channel(488769306524385301)
        if channel is None:
            return await ctx.send("Salon introuvable")
        text = text.split('\n')
        try:
            fr_text, en_text = text[0].replace('\\n','\n'), text[1].replace('\\n','\n')
        except IndexError:
            await ctx.send("Il manque le texte anglais")
            return
        emb = discord.Embed(color=16106019, timestamp=self.bot.utcnow())
        emb.add_field(name='Français', value=fr_text, inline=False)
        emb.add_field(name='English', value=en_text, inline=False)
        msg = await channel.send(embed=emb)
        for emoji in self.upvote_emojis:
            await msg.add_reaction(emoji)
        await self.add_success_reaction(ctx.message)

    @main_idea.command(name='valid')
    async def idea_valid(self, ctx: MyContext, msg_id:int, valid:bool=True):
        """Marque une idée comme étant ajoutée à la prochaine MàJ"""
        chan = ctx.bot.get_channel(929864644678549534) if self.bot.beta else ctx.bot.get_channel(488769306524385301)
        if chan is None:
            return await ctx.send("Salon introuvable")
        try: # try to fetch message from ideas channel
            msg = await chan.fetch_message(msg_id)
        except discord.DiscordException as err:
            # something went wrong (invalid message ID, or any other Discord API error)
            return await ctx.send(f"`Error:` {err}")
        if len(msg.embeds) != 1:
            return await ctx.send("Nombre d'embeds invalide")
        emb = msg.embeds[0]
        if valid: # if the idea should be marked as soon-released
            emb.color = discord.Color(10146593)
        else:
            emb.color = discord.Color(16106019)
        await msg.edit(embed=emb)
        await self.add_success_reaction(ctx.message)

async def setup(bot):
    await bot.add_cog(Admin(bot))
