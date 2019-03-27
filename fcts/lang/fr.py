#!/usr/bin/env python
#coding=utf-8

current_lang = {'current':'fr'}

activity={"rien":"rien",
"play":"joue à",
"stream":"stream",
"listen":"écoute",
"watch":"regarde"}

admin={
    "change_game-0":"Sélectionnez *play*, *watch*, *listen* ou *stream* suivi du nom",
    "msg_2-0":"Opération en cours...",
    "msg_2-1":"Aucun membre affecté",
    "msg_2-2":"1 membre affecté",
    "msg_2-3":"membres affectés",
    "bug-0":"Le bug n°{} n'a pas été trouvé",
    "emergency":"Une situation d'urgence vient d'être déclarée pour le bot. Cela peut être le cas lorsque quelqu'un tente de prendre le contrôle de mon code.\n\
Pour limiter les dégâts, j'ai été forcé de quitter immédiatement l'intégralité des serveurs sur lesquels je me trouvais, en espérant qu'il ne soit pas trop tard.\n\
Pour plus d'informations sur l'état actuel de la crise, rendez-vous sur mon serveur officiel : https://discord.me/z_bot (vérifiez le lien depuis la documentation si celui-ci ne fonctionne plus : https://zbot.rtfd.io)"
    }

aide={"no-subcmd":"La commande {0.name} n'a aucune sous-commande",
"mods":['Modération :','Autres :'],
"footer":"Entrez {}help commande pour plus d'informations sur une commande",
"no-desc-cog":"Aucune description pour ce module.",
"no-desc-cmd":"Aucune description pour cette commande",
"cmd-not-found":"Aucune commande nommée \"{}\"",
"subcmd-not-found":"Cette commande ne possède aucune sous-commande nommée \"{}\""}

bvn={"aide":"""__**Bienvenue dans le module des message de join et de leave**__

Ce module vous sert à configurer un message automatique à chaque fois qu'un membre rentre ou sort de votre serveur.

__**La configuration**__

`1-` Pour configurer le salon où ces messages s'écrivent, entrez `!config change welcome_channel` suivi de l'identifiant du salon (clic droit -> "Copier l'identifiant" pour ordinateur, ou rester appuyez sur le salon -> "Copier l'identifiant" pour téléphone, mais il vous faudra avoir activé le mode développeur pour obtenir cette option).
`2-` Pour configurer un message, entrez `!config change <welcome|leave> <message>`. Pour ce message vous pouvez utiliser les variables suivantes :
 - `{user}` mentionne le membre
 - `{server}` affiche le nom du serveur
 - `{owner}` affiche le nom du propriétaire du serveur
 - `{member_count}` affiche le nombre actuel de membres
"""}

cases={"no-user":"Impossible de trouver cet utilisateur",
    "not-found":"Ce casier n'a pas été trouvé :confused:",
    "reason-edited":"La raison du casier n°{} a bien été modifiée !",
    "deleted":"Le casier n°{} a bien été supprimé !",
    "cases-0":"{} casiers trouvés : ({}-{})",
    "search-0":"**Membre:** {U}\n**Type:** {T}\n**Moderateur:** {M}\n**Date:** {D}\n**Raison:** *{R}*",
    "search-1":"**Membre:** {U}\n**Serveur:** {G}\n**Type:** {T}\n**Moderateur:** {M}\n**Date:** {D}\n**Raison:** *{R}*",
    'title-search':'Casier #{}',
    'no_database':"En raison d'une panne temporaire de la base de donnée, cette commande a été désactivée"}

events={'mp-adv':"Vous cherchez sans doute à m'inviter sur ce serveur ? Si c'est le cas, je ne peux pas le rejoindre avec une simple invitation. Il faut qu'un administrateur utilise mon propre lien d'invitation, ici : <https://bot.discord.io/zbot> :wink:"}

errors={"cooldown":"Vous êtes en cooldown pour cette commande. Veuillez attendre encore {0} secondes...",
"badarguments":"Oups, impossible de convertir le paramètre `{0}` en type \"{1}\" :confused:",
"missingargument":"Oups, il manque l'argument \"{0}\" {1}",
"membernotfound":"Impossible de trouver le membre `{0}` :confused:",
"usernotfound":"Impossible de trouver l'utilisateur `{0}` :confused:",
"disabled":"La commande {0} est désactivée",
"duration":"La durée `{0}` est invalide"}

find={"user-0":"Nom : {}\nID : {}",
"user-1":"Nom : {name}\nID : {id}\nRangs : {rangs}\nServeurs : {servers}\nPropriétaire de : {own}\nLangues : {lang}\nA voté : {vote}\nCarte d'xp : {card}",
"user-2":"Utilisateur introuvable",
"guild-0":"Serveur introuvable",
"guild-1":"Nom : {}\nID : {}\nPropriétaire : {} ({})\nMembres : {} (dont {} bots)\nLangue : {}",
"chan-0":"Salon introuvable",
"chan-1":"Nom : {}\nID : {}\nServeur : {} ({})",
"help":"Cette commande permet de retrouver un serveur ou un salon parmi tout les serveurs sur lequel est le bot. Vous pouvez aussi rechercher les informations d'un utilisateur Discord, peu importe si il partage un serveur avec moi !\
La syntaxe est `!find <user|channel|guild> <ID>`"}

fun={"count-0":"Comptage en cours...",
    "count-1":"Sur les {} derniers messages, vous en avez posté {} ({}%)",
    "count-2":"Mais vous voulez faire exploser Discord ! {e} Pour des raisons évidentes de performances, je vais vous imposer une limite à {l} messages.",
    "count-3":"Oups, il m'est impossible de lire l'historique de ce salon. Veuillez vérifier mes permissions...",
    "fun-list":"Voici la liste des commandes fun disponibles :",
    "no-fun":"Les commandes fun ont été désactivées sur ce serveur. Pour voir leur liste, regardez https://zbot.rtfd.io/en/v3/fun.html",
    "osekour":["Attends, je finis de regarder mon film","On arrive ! Mais pourquoi ne répondez-vous plus ? Ne simulez pas la mort !","Oui on sait qu'il y a du feu, on n'a pas besoin de venir : on fait un barbecue à la caserne","*Les secours sont actuellement indisponibles, veuillez attendre la fin de la pause*","*Ce numéro n'existe pas. Veuillez réessayer avec un autre numéro.*","*Maintenance de la ligne en cours. Veuillez réessayer d'ici 430 heures.*","*Votre forfait mobile est arrivé à son terme. Vous pouvez en racheter un pour 86,25€*","Encore 2 tomes du Seigneur des Anneaux à finir de lire, et je suis à vous !","Merci de ne pas nous déranger pendant les fêtes","Désolé, il y a plus de 3 flocons de neige: nous sommes coincés au garage","Il va falloir attendre la fin de notre grève... Comment ça, vous n'êtes pas au courant ?! Ça fait pourtant bien deux mois que nous avons commencé !"],
    "react-0":"Impossible de trouver le message correspondant. Il faut rentrer l'ID du message en 1er argument, et l'émoji en 2e :upside_down:\n Vérifiez aussi que je possède la permission de lire l'historique des messages !",
    "thanos":["{0} a été épargné par Thanos","Thanos a décidé de réduire {0} en cendres. Pour le bien de l'humanité..."],
    "piece-0":["Pile !","Face !"],
    "piece-1":"Raté, c'est tombé sur la tranche !",
    "calc-0":"Le résultat prend trop de temps à charger :/",
    "calc-1":"Les solutions du calcul `{}` sont `{}`",
    "calc-2":"Les solutions du calcul `{c}` sont `{l[0]}` et `{l[1]}`",
    "calc-3":"La solution du calcul `{}` est `{}`",
    "calc-4":"Le calcul `{}` n'a aucune solution",
    "calc-5":"Oups, une erreur est apparue : `{}`",
    "no-reaction":"Impossible d'ajouter les réactions. Vérifiez mes permissions",
    "cant-react":"Je n'ai pas les permissions suffisantes pour envoyer des réactions !",
    "no-emoji":"Impossible de trouver cet emoji !",
    "vote-0":"Vous ne pouvez pas mettre plus de 20 choix, encore moins un nombre négatif de choix !",
    "blame-0":"Liste des noms disponibles pour le membre **{}**",
    "no-database":"Notre base de donnée étant hors ligne, l'accès aux commandes fun est restreint aux personnes ayant la permission de Gérer le Serveur",
    "no-embed-perm":"Je ne possède pas la permission \"Intégrer des liens\" :confused:",
    "embed-error":"Une erreur est survenue: `{}`",
    "invalid-city":"Nom de ville invalide"
    }

infos={"text-0":"""Bonjour ! Moi c'est {0} !

Je suis un bot qui permet de faire *beaucoup* de choses : de la modération, des mini-jeux, un système d'xp, des statistiques et plein d'autres commandes plus ou moins utiles ! 
Vous pouvez commencer par taper `!help` dans ce tchat pour voir la liste des commandes disponibles, puis `!config see` vous permettra de voir les options de configuration (un site web est en préparation). 

Pour m'avoir aidé dans la création du bot, mon propriétaire et moi souhaitons remercier Awhikax pour son soutien apporté lors des différentes crises, Aragorn1202 pour toutes ses idées et ses phrases pleines de bon sens, Adri526 pour tous ces magnifiques logos, émojis et images de profil, et Pilotnick54 pour relire et corriger mon anglais !

:globe_with_meridians: Quelques liens pourront vous être utiles : 
:arrow_forward: Mon serveur Discord : http://discord.gg/N55zY88
:arrow_forward: Un lien pour m'inviter dans un autre serveur : <https://bot.discord.io/zbot>
:arrow_forward: La documentation du bot : <https://zbot.rtfd.io/>
:arrow_forward: Le compte Twitter de mon créateur : <https://twitter.com/z_runnerr>

Bonne journée !""",
"docs":"Voici le lien vers la documentation du bot :",
"stats-title":"**Statistiques du bot**",
"stats":"""**Version du bot :** {} \n**Nombre de serveurs :** {} \n**Nombre de membres visibles :** {} (dont {} **bots**)\n**Nombre de lignes de code :** {}\n**Langues utilisées :** {} \n**Version de Python :** {} \n**Version de la bibliothèque `discord.py` :** {} \n**Charge sur la mémoire vive :** {} GB \n**Charge sur le CPU :** {} % \n**Temps de latence de l'api :** {} ms\n**Nombre total d'xp gagné :** {}xp""",
"admins-list":"Les administrateurs de ce bot sont : {}",
"prefix":"Liste des préfixes actuellement utilisables :"}

infos_2={"membercount-0":"Nombre de membres total",
"membercount-1":"Nombre de bots",
"membercount-2":"Nombre d'humains",
"membercount-3":"Nombre de membres connectés"}

keywords={"depuis":"depuis",
          "nom":"nom",
          "online":"en ligne",
          "idle":"inactif",
          "dnd":"ne pas déranger",
          "offline":"hors ligne",
          "oui":"oui",
          "non":"non",
          "none":"aucun",
          "low":"faible",
          "medium":"moyen",
          "high":"élevé",
          "extreme":"extrême",
          "aucune":"aucune",
          "membres":"membres",
          "subcmds":"sous-commandes",
          "ghost":"Fantôme"
          }

kill={"list":["Oh toi, tu vas mourir !",
          "***BOUM !*** {1} est tombé dans un piège posé par {0} !",
          "Heureusement que le sol a amorti la chute de {1} !",
          "{0} a crié \"Fus Roh Dah\" alors que {1} était à coté d'une falaise...",
          "Eh non, tu ne peux pas arreter les balles avec tes mains {1} :shrug:",
          "Il faut être __dans__ l’ascenseur {1}, pas __au-dessus__...",
          "{1} est resté trop près des enceintes lors d'un concert de heavy metal.",
          "Rester à moins de 10m d'une explosion atomique, ce n'était pas une bonne idée {1}...",
          "Non ! Les doubles sauts ne sont pas possibles {1} !",
          "{1} a imité Icare... splash.",
          "C'est bien d'avoir un pistolet à portails {1}, encore faut il ne pas en ouvrir un au dessus des piques....",
          "{1} est mort. Paix à son âme... :sneezing_face:",
          "{0} a tué {1}",
          "{1} a été shot par {0}",
          "Bye {1} ! :ghost:",
          "{1} a vu tomber une enclume volante... sur sa tête :head_bandage:",
          "{1} part se suicider après que {0} ai coupé sa connexion",
          "Attention {1} ! Le feu, ça brûle :fire:",
          "{1} est parti sans pelle lors d'une attaque zombie",
          "{1} a tenté de faire un calin à un creeper",
          "{1}, les bains de lave sont chauds, mais la lave, ça brûle...",
          "{1} a tenté un rocket jump",
          "Il ne fallait pas écouter la jolie mélodie de la Lullaby, {1} :musical_note:",
          "{2}.exe *a cessé de fonctionner*"
          ]}

logs={"slowmode-enabled":"Slowmode activé dans le salon {channel} ({seconds}s)",
"slowmode-disabled":"Slowmode désactivé dans le salon {channel}",
"clear":"{number} messages supprimés dans {channel}",
"kick":"{member} a été expulsé du serveur (raison : {reason} | casier #{case})",
"ban":"{member} a été banni du serveur (raison : {reason} | casier #{case})",
"unban":"{member} n'est plus banni de ce serveur (raison : {reason})",
"mute-on":"{member} est maintenant muet (raison : {reason} | casier #{case})",
"mute-off":"{member} n'est plus muet",
"softban":"{member} a été 'softban' (raison : {reason} | casier #{case})",
"warn":"{member} a reçu un avertissement : {reason} (casier #{case})",
"tempmute-on":"{member} est maintenant muet pour {duration} (raison : {reason} | casier #{case})",
"d-autounmute":"unmute automatique",
"d-unmute":"unmute par {}",
"d-invite":"Automod (invitation Discord)",
"d-young":"Automod (compte trop récent)",
"d-gived_roles":"Action automatique (config gived_roles)",
"d-memberchan":"Action automatique (config membercount)"}

mc={"contact-mail":"Si vous constatez une erreur dans les informations données, merci de me contacter rapidement, ou de rapporter l'erreur directement [sur le site](https://fr-minecraft.net).",
    "serv-title":"Informations du serveur {}",
    "serv-0":"Nombre de joueurs",
    "serv-1":"Liste des 20 premiers joueurs connectés",
    "serv-2":"Liste des joueurs connectés",
    "serv-3":"Latence",
    "serv-error":"Oups, une erreur inconnue s'est produite. Veuillez réessayer plus tard :confused:",
    "no-api":"Erreur : Impossible de se connecter à l'API",
    "no-ping":"Erreur : Impossible de ping ce serveur",
    "success-add":"Un message avec les détails du serveur {} a bien été ajouté dans le salon {} !",
    "cant-embed":"Impossible d'envoyez l'embed. Vérifiez que la permission \"Embed links\" est bien activée svp",
    "names":("Bloc","Entité","Item","Commande","Progrès"),
    "entity-help":"Cette commande permet d'obtenir des informations sur n'importe quelle entité de Minecraft. Vous pouvez donner son nom complet ou partiel, en français ou en anglais, ou même son identifiant. Il suffit d'entrer `!mc entity <nom>`",
    "block-help":"Cette commande permet d'obtenir des informations sur n'importe quel bloc de Minecraft. Vous pouvez donner son nom complet ou partiel, en français ou en anglais, ou même son identifiant. Il suffit d'entrer `!mc block <nom>`",
    "item-help":"Cette commande permet d'obtenir des informations sur n'importe quel item de Minecraft. Vous pouvez donner son nom complet ou partiel, en français ou en anglais, ou même son identifiant. Il suffit d'entrer `!mc item <nom>`",
    "cmd-help":"Cette commande permet d'obtenir des informations sur n'importe quelle commande de Minecraft. Il suffit d'entrer `!mc entity <nom>`",
    "adv-help":"Cette commande permet d'obtenir des informations sur n'importe quel progrès du jeu Minecraft (parfois ausis appelé 'avancement'). Il vous suffit d'entrer le nom ou l'identifiant du progrès.",
    "no-entity":"Entité introuvable",
    "no-block":"Bloc introuvable",
    "no-item":"Item introuvable",
    "no-cmd":"Commande introuvable",
    "no-adv":"Progrès introuvable",
    "mojang_desc":{'minecraft.net':'Site officiel',
      'session.minecraft.net':'Sessions multijoueurs (obsolètes)',
      'account.mojang.com':'Site de gestion des comptes Mojang',
      'authserver.mojang.com':"Serveur d'authentification",
      'sessionserver.mojang.com':'Sessions multijoueurs',
      'api.mojang.com':"Service d'API fournit par Mojang",
      'textures.minecraft.net':'Serveur de textures (skin & capes)',
      'mojang.com':'Site officiel'},
    "dimensions":"Largeur: {d[0]}\nLongueur: {d[1]}\nHauteur: {d[2]}",
    "entity-fields":('ID','Type','Points de vie','Points d\'attaque',"Points d'expérience lâchées à la mort","Biomes de prédilection","Version d'ajout"),
    "block-fields":("ID","Taille d'un stack","Onglet du mode créatif","Points de dégâts","Points de durabilité","Outil capable de le détruire","Mobs pouvant lâcher cet item","Version d'ajout"),
    "item-fields":('ID',"Taille d'un stack",'Onglet du mode créatif','Points de dégâts',"Points de durabilité","Outil capable de le détruire","Mobs pouvant lâcher cet item","Version d'ajout"),
    "cmd-fields":("Nom","Syntaxe","Exemples","Version d'ajout"),
    "adv-fields":("Nom","Identifiant","Type","Action","Parent","Enfants","Version d'ajout"),
    }

modo={"slowmode-0":"Le slowmode est désormais désactivé dans ce salon.",
    "slowmode-1":"Impossible de mettre une fréquence supérieure à deux minutes",
    "slowmode-2":"Le channel {} est désormais en slowmode.\nAttendez {} secondes avant d'envoyer un message.",
    "slowmode-3":"Cette valeur est invalide",
    "slowmode-info":"Le slowmode de ce salon est actuellement à {} secondes",
    "cant-slowmode":"Oups, je n'ai pas la permission de `Gérer le salon` :confused:",
    "clear-0":"{} messages supprimés !",
    "need-manage-messages":"Permission \"Gérer les messages\" manquante :confused:",
    "need-read-history":"Oups, il me manque la permission de \"Voir les anciens messages\" :confused: ",
    "clear-1":"Je ne peux pas supprimer si peu de messages",
    "clear-nt-found":"Hum... impossible de supprimer ces messages. Discord me dit qu'ils n'existent pas :thinking:",
    "cant-kick":"Permission 'Kick members' manquante :confused:",
    "kick":"Le membre {} a bien été expulsé du serveur, avec la raison `{}`",
    "staff-kick":"Vous ne pouvez pas expulser un autre membre du staff !",
    "kick-noreason":"Vous venez d'être expulsé du serveur {} :confused:",
    "kick-reason":"Vous venez d'être expulsé du serveur {} :confused:\nRaison : {}",
    "kick-1":"Il semble que ce membre soit trop haut pour que je puisse l'expulser :thinking:",
    "error":"Oups, une erreur inconnue est survenue. Réessayez plus tard ou contactez le support",
    "warn-mp":"Vous avez reçu un avertissement de la part du serveur *{}* : \n{}",
    "staff-warn":"Vous ne pouvez pas avertir un autre membre du staff !",
    "warn-1":"Le membre `{}` a bien reçu son avertissement, avec la raison `{}`",
    "warn-bot":"Je ne peux pas avertir un bot ^^",
    "warn-but-db":"Notre base de donnée étant hors ligne, l'avertisement n'a pas pu être enregistré. Néanmoins le membre a bien reçu son avertissement en MP",
    "staff-mute":"Vous ne pouvez pas empêcher de parler un autre membre du staff ",
    "mute-1":"Le membre {} a bien été réduit au silence pour la raison `{}` !",
    "mute-created":"Rôle `muted` créé avec succès !",
    "no-mute":"Oups, il semble que le rôle `muted` n'existe pas :confused: Veuillez le créer et lui attribuer les permissions manuellement.",
    "cant-mute":"Oups, il semble que je ne possède pas les permissions suffisantes pour cela... Veuillez m'attribuer la permission `gérer les rôles` avant de continuer.",
    "mute-high":"Oups, il semble que le rôle `muted` soit trop haut pour que je puisse le donner... Veuillez fixer ce problème en plaçant mon rôle plus haut que le rôle `muted`.",
    "already-mute":"Ce membre est déjà muet !",
    "already-unmute":"Ce membre n'est pas muet !",
    "unmute-1":"Le membre {} peut à nouveau parler !",
    "cant-ban":"Permission 'Ban members' manquante :confused:",
    "staff-ban":"Vous ne pouvez pas bannir un autre membre du staff !",
    "ban-noreason":"Vous venez d'être banni du serveur {} :confused:",
    "ban-reason":"Vous venez d'être banni du serveur {} :confused:\nRaison : {}",
    "ban":"Le membre {} a bien été banni du serveur, avec la raison `{}`",
    "ban-1":"Il semble que ce membre soit trop haut pour que je puisse le bannir :thinking:",
    "ban-list-title-0":"Liste des membres bannis du serveur '{}'",
    "ban-list-title-1":"Liste des 45 premiers membres bannis du serveur '{}'",
    "ban-list-title-2":"Liste des 60 premiers membres bannis du serveur '{}'",
    "ban-list-error":"Oups, il y a trop de membres à afficher :confused:",
    "no-bans":"Aucun membre ne semble être banni de ce serveur",
    "unban":"Le membre {} n'est plus banni de ce serveur",
    "cant-find-user":"Oups, impossible de trouver l'utilisateur **{}**",
    "ban-user-here":"Cette personne ne fait pas partie des membres bannis :upside_down:",
    "caps-lock":"Hey {}, attention aux majuscules !",
    "cant-emoji":"Oups, il me manque la permission `Gérer les émojis` :confused:",
    "emoji-valid":"L'émoji {} a été modifié pour n'autoriser que les rôles `{}`",
    "wrong-guild":"Oups, il semble que cet émoji n'appartienne pas à ce serveur :thinking:",
    "emoji-renamed":"L'émoji {} a bien été renommé !",
    "cant-pin":"Oups, je ne dispose pas de la permission d'épingler des messages",
    "pin-error":"Oups, je n'arrive pas à retrouver ce message (Erreur : `{}`)",
    "pin-error-3":"Oups, impossible d'épingler ce message (Avez-vous plus de 50 messages épinglés ?). Erreur : `{}`",
    "react-clear":"Impossible de retrouver ce message :confused:",
    "em-list":"{} (`:{}:`) ajouté le {} {}",
    "em-private":"[Restreint]",
    "em-list-title":"Emojis du serveur {}",
    "tempmute-1":"Le membre {} a bien été réduit au silence pour la raison `{}`, pendant {} !",
    }

morpion={'user-begin':'{}, à toi de commencer !',
        'bot-begin':'Allez hop, je commence !',
        'tip':"\n*Pour jouer, il suffit de taper un nombre entre 1 et 9, correspondant à la case choisie. Je joue les rouges, toi les bleus*",
        'nul':"Match nul, personne n'a gagné...",
        'too-late':"Vous avez mis trop de temps à vous décider. Fin de la partie !",
        'pion-1':'Il y a déjà un pion sur cette case !',
        'pion-2':'Case saisie invalide !',
        'win-1':"Bien joué, {} a gagné !",
        'win-2':"J'ai gagné ! Fin du match !"}

perms={"perms-0":"Le membre/rôle {} n'a pas été trouvé",
        "perms-1":"**Permission de '{}' :**\n\n"
       }

rss={"yt-help":"Pour rechercher une chaîne youtube, vous devez entrer l'identifiant de cette chaîne. Vous la trouverez à la fin de l'url de la chaine, elle peut être soit le nom, soit une suite de caractères aléatoires. \
*Astuce : certaines chaînes sont déjà renseignées dans mon code. Vous pouvez parfois vous contenter de mettre `neil3000` ou `Oxisius`* :wink:",
"tw-help":"Pour rechercher une chaîne twitter, vous devez entrer l'identifiant de cette chaîne. Vous la trouverez à la fin de l'url de la chaîne, elle correspond généralement au nom de l'utilisateur. \
Par exemple, pour %https://twitter.com/Mc_AsiliS*, il faut rentrer `Mc_AsiliS`",
"web-help":"Pour rechercher un flux rss à partir de n'importe quel site web, il suffit d'entrer l'url du flux rss/atom en paramètre. Si le flux est valide, je vous renverrai le dernier article posté sur ce site. \
*Astuce : certains flux rss sont déjà renseignées dans mon code. Vous pouvez parfois vous contenter de mettre `fr-minecraft` ou `minecraft.net`* :wink:",
"web-invalid":"Oups, cette adresse url est invalide :confused:",
"nothing":"Je n'ai rien trouvé sur cette recherche :confused:",
"success-add":"Le flux rss de type '{}' avec le lien <{}> a bien été ajouté dans le salon {} !",
"invalid-link":"Oups, cette adresse url est invalide ou incomplète :confused:",
"fail-add":"Une erreur s'est produite lors du traitement de votre réponse. Merci de réessayer plus tard, ou de contacter le support du bot (entrez la commande `about` pour le lien du serveur)",
"flow-limit":"Pour des raisons de performances, vous ne pouvez pas suivre plus de {} flux rss par serveur.",
"yt-form-last":"""{logo}  | Voici la dernière vidéo de {author}:
{title}
Publiée le {date}
Lien : {url}
""",
"tw-form-last":"""{logo}  | Voici le dernier tweet de {author}:
Écrit le {date}

{title}

Lien : {url}
""",
"twitch-form-last":"""{logo}  | Voici la dernière vidéo de {author}:
{title}
Publiée le {date}
Lien : {url}
""",
"web-form-last":"""{logo}  | Voici le dernier post de {author}:
**{title}**
*Ecrit le {date}*
Lien : {link}""",
"yt-default-flow":"{logo}  | Nouvelle vidéo de {author} : **{title}**\nPubliée le {date}\nLien : {link}\n{mentions}",
"tw-default-flow":"{logo}  | Nouveau tweet de {author} ! ({date})\n\n{title}\n\nLien : {link}\n\n{mentions}",
"twitch-default-flow":"{logo}  | Nouveau live de {author} ! ({date})\n\n{title}\n\nLien : {link}\n\n{mentions}",
"web-default-flow":"{logo}  | Nouveau post sur {author} ({date}) :\n    {title}\n\n{link}\n\n{mentions}",
"list":"*Entrez le numéro du flux à modifier*\n\n**Lien - Type - Salon - Roles**\n",
"list2":"*Entrez le numéro du flux à supprimer*\n\n**Lien - Type - Salon**\n",
'tw':'Twitter',
'yt':'YouTube',
'twitch':'Twitch',
'web':'Web',
'mc':'Minecraft',
'choose-mentions-1':"Veuillez choisir le flux à modifier",
"choose-delete":"Veuillez choisir le flux à supprimer",
"too-long":"Vous avez trop attendu, désolé :hourglass:",
"no-roles":"Aucun rôle n'a été configuré pour l'instant.",
"roles-list":"Voici la liste des rôles déjà mentionnés : {}",
"choose-roles":"Quels seront les rôles à mentionner ?",
"not-a-role":"Le rôle `{}` est introuvable. Réessayez :",
"roles-0":"Ce flux a bien été modifié pour mentionner les rôles {}",
"roles-1":"Ce flux a bien été modifié pour ne mentionner aucun rôle",
"no-feed":"Oups, vous n'avez aucun flux rss à gérer !",
"delete-success":"Le flux a été supprimé avec succès !",
"no-db":"La base de donnée étant actuellement hors ligne, cette fonctionnalité est temporairement désactivée :confused:",
"guild-complete":"{} flux rss ont correctement été rechargés, en {} secondes !",
"guild-error":"Une erreur est survenue pendant la procédure : `{}`\nSi vous pensez que cette erreur ne vient pas de vous, vous pouvez en avertir le support",
"guild-loading":"Rechargement en cours {}",
"move-success":"Le flux rss n°{} a bien été bougé dans le salon {} !",
"change-txt":"""Le message actuel contient \n```\n{text}\n```\nVeuillez entrer le texte à utiliser lors d'un nouveau post. Vous pouvez utiliser plusieurs variables, dont voici la liste :
- `{author}` : l'auteur du post
- `{channel}` : le salon Discord dans lequel est posté le message
- `{date}` : la date du post (UTC)
- `{link}` ou `{url}` : un lien vers le post
- `{logo}` : un emoji représentant le type de post (web, Twitter, YouTube...)
- `{mentions}` : la liste des rôles mentionnés
- `{title}` : le titre du post""",
"text-success":"Le texte du flux n°{} a bien été modifié ! Nouveau texte : \n```\n{}\n```",
"invalid-flow":"Cet url est invalide (flux rss vide ou inaccessible) :confused:",
"research-timeout":"La page web a mis trop de temps à répondre, j'ai dû interrompre le processus :eyes:"
}

server={"config-help":"Cette commande sert principalement à configurer votre serveur. En faisant `!config see [option]` vous obtiendrez l'aperçu des configurations actuelles, \
et les administrateurs du serveur peuvent entrer `!config change <option> role1, role2, role3...` pour modifier une configuration, ou `!config del <option>` pour réinitialiser \
l'option (`!config change <option> del` fonctionne de même).",
        "change-0":"Cette option n'existe pas :confused:",
        "change-1":"Oups, une erreur interne est survenue...",
        "change-2":"La valeur de l'option '{}' a bien été effacée",
        "change-3":"Le rôle '{}' n'a pas été trouvé :confused: (Vérifiez les majuscules et les caractères spéciaux)",
        "change-4":"L'option '{}' attend un paramètre de type booléen (True/False) en valeur :innocent:",
        "change-5":"Le salon '{}' n'a pas été trouvé :confused: (Entrez la mention, le nom exact ou l'identifiant du ou des salon(s)",
        "change-6":"L'option '{}' attend un nombre en paramètre :innocent:",
        "change-7":"Cette langue n'est pas disponible. Voici la liste des langues actuellement supportées : {}",
        "change-8":"Ce niveau n'existe pas. Voici la liste des niveaux actuellement disponibles : {}",
        "change-9":"L'émoji `{}` n'a pas été trouvé",
        "change-role":"L'option '{}' a bien été modifiée avec les rôles suivants : {}",
        "change-bool":"L'option '{}' a bien été modifiée avec la valeur *{}*",
        "change-textchan":"L'option '{}' a bien été modifiée avec les salons {}",
        "change-text":"L'option '{}' a bien été remplacée par le texte suivant : \n```\n{}\n```",
        "change-prefix":"Le préfixe a bien été remplacé par `{}`",
        "change-lang":"La langue du bot est maintenant en `{}`",
        "change-raid":"Le niveau de sécurité anti-raid est maintenant défini à **{}** ({})",
        "change-emojis":"Les émojis pour l'option '{}' sont maintenant {}",
        "new_server":"Votre serveur vient d'être enregistré pour la première fois dans notre base de donnée. Félicitations :tada:",
        "see-0":"Entrez `!config help` pour plus de détails",
        "see-1":"Configuration du serveur {}",
        "change-prefix-1":"Ce préfixe est trop long pour être utilisé !",
        "wrong-prefix":"Oups, il semble que ce préfixe est invalide :thinking: Si le problème persiste, veuillez en choisir un autre",
        "opt_title":"Option '{}' du serveur {}",
        "not-found":"Le serveur {} n'a pas encore été enregistré dans la base de donnée"
        }

server_desc={"prefix":"Préfixe actuel du bot : {}",
             "language":"Langue actuelle du bot pour ce serveur : **{}**",
             "clear":"Liste des rôles qui peuvent utiliser la commande 'clear' : {}",
             "slowmode":"Liste des rôles qui peuvent utiliser les commandes 'slowmode' et 'freeze' : {}",
             "mute":"Liste des rôles qui peuvent utiliser la commande 'mute' : {}",
             "kick":"Liste des rôles qui peuvent utiliser la commande 'kick' : {}",
             "ban":"Liste des rôles qui peuvent utiliser la commande 'ban' : {}",
             "warn":"Liste des rôles pouvant utiliser les commandes 'warn' et 'case' : {}",
             "say":"Liste des rôles qui peuvent utiliser la commande 'say' : {}",
             "hunter":"Liste des salons dans lesquels le jeu *Hunter* est actif : {}",
             "welcome_channel":"Liste des salons dans lesquels envoyer les messages de bienvenue/quit : {}",
             "welcome":"Message envoyé lorsqu'un membre arrive : {}",
             "leave":"Message envoyé lorsqu'un membre repart : {}",
             "gived_roles":"Liste des rôles donnés automatiquement aux nouveaux membres : {}",
             "bot_news":"Liste des salons dans lesquels envoyer les news du bot : {}",
             "modlogs_channel":"Salon dans lequel sont envoyés les logs de modération : {}",
             "save_roles":"Les rôles doivent-ils être sauvegardés lorsqu'un membre part, au cas où il revienne ? {}",
             "poll_channels":"Liste des salons dans lesquels les réactions :thumbsup: et :thumbsdown: seront automatiquement ajoutées à chaque message : {}",
             "enable_xp":"Le système d'xp doit-il être activé ? {}",
             "levelup_msg":"Message envoyé lorsqu'un membre gagne un niveau d'xp : {}",
             "anti_caps_lock":"Le bot doit-il envoyer un message lorsqu'un membre envoie trop de majuscules ? {}",
             "enable_fun":"Les commandes répertoriées dans la commande `!fun` sont-elles activées ? {}",    
             "membercounter":"Salon affichant dans son nom le nombre de membres : {}",
             "anti_raid":"Niveau de la protection anti-raid : {} \n*([Documentation](https://zbot.rtfd.io/en/latest/moderator.html#anti-raid))*",
             "vote_emojis":"Emojis utilisés pour les réactions de vote : {}",
             "help_in_dm":"Envoyer le message d'aide en message privés ? {}",
             "muted_role":"Rôle utilisé pour rendre les gens muets : {}"}

stats_infos={"not-found":"Impossible de trouver {N}",
            "member-0":"Surnom",
            "member-1":"Créé le",
            "member-2":"A rejoint le",
            "member-3":"Position d'arrivée",
            "member-4":"Statut",
            "member-5":"Activité",
            "member-6":"Administrateur",
            "role-0":"Identifiant",
            "role-1":"Couleur",
            "role-2":"Mentionable",
            "role-3":"Nombre de membres",
            "role-4":"Affiché séparément",
            "role-5":"Position hiérarchique",
            "role-6":"Unique membre possédant ce rôle",
            "user-0":"Sur ce serveur ?",
            "emoji-0":"Animé",
            "emoji-1":"Intégré par Twitch",
            "emoji-2":"Chaine de caractères (pour bot)",
            "emoji-3":"Serveur sur lequel est l'émoji",
            "textchan-0":"Catégorie",
            "textchan-1":"Description",
            "textchan-2":"NSFW",
            "textchan-3":"Nombre de webhooks",
            "textchan-4":":warning: Permissions manquantes",
            "textchan-5":"Salon",
            "voicechan-0":"Salon vocal",
            "guild-0":"Serveur",
            "guild-1":"Propriétaire",
            "guild-2":"Région",
            "guild-3":"Texte : {} | Vocal : {} ({} catégories)",
            "guild-4":"Membres connectés",
            "guild-5":"Nombre d'émojis",
            "guild-6":"Nombre de salons",
            "guild-7":"{} dont {} bots ({} connectés)",
            "guild-8":"Authentification à deux facteurs",
            "guild-9":"Niveau de sécurité",
            "guild-10":"Temps avant d'être AFK",
            "guild-11.1":"20 premiers rôles ({} total)",
            "guild-11.2":"Liste des rôles ({} total)",
            "guild-12":"Nombre d'invitations",
            "inv-0":"Adresse url",
            "inv-1":"Créateur",
            "inv-2":"Utilisations",
            "inv-3":"Temps restant",
            "inv-4":"Invitation",
            "inv-5":"Si une information vous semble manquante, c'est malheureusement parce que Discord ne l'a pas communiquée",
            "categ-0":"Catégorie",
            "categ-1":"Position",
            "categ-2":"Texte : {} | Vocal : {}",
             }

users = {'invalid-card':'Ce style est invalide. Voici la liste des styles que vous pouvez utiliser : {}',
        'missing-attach-files':'Oups, il me manque la permission d\'Attacher des Fichiers :confused:',
        'changed-0':'Votre carte d\'xp utilise maintenant le style {}',
        'changed-1':'Oups, une erreur interne est survenue pendant le traitement de la requête. Réessayez plus tard ou contactez le support.',
        'card-desc':"Voici un exemple de votre carte d'xp. Vous pouvez entrer la commande `profile card <style>` pour changer le style\n*Votre carte d'xp ne se réactualisera que lorsque vous aurez gagné de l'xp*"}

xp = {'card-level':'NIVEAU',
        'card-rank':'RANG',
        '1-no-xp':"Vous ne possédez pas encore d'xp !",
        '2-no-xp':"Ce membre ne possède pas d'xp !",
        "del-user":"<deleted user>",
        "low-page":"Impossible d'afficher un numéro de page négatif !",
        "high-page":"Il n'y a pas autant de pages !",
        "top-title-1":"Classement global",
        "top-name":"__Top {}-{} (page {}/{}) :__",
        "default_levelup":"{user} vient de passer **niveau {level}** ! GG !",
        "top-your":"Votre niveau"}