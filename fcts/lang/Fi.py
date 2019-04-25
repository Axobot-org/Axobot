#!/usr/bin/env python
#coding=utf-8

current_lang = {'current':'fi'}

activity={"rien":"Ei mitään",
"play":"soittaa",
"stream":"striimaa",
"listen":"listening to",
"watch":"katsoo"}

admin={
    "change_game-0":"Valitse *play*, *watch*, *listen* tai *stream* seurattu nimellä",
    "msg_2-0":"Operaatio käynnissä...",
    "msg_2-1":"Ei vaikuttavia käyttäjiä",
    "msg_2-2":"1 vaikuttanut käyttäjä",
    "msg_2-3":"vaikutetut käyttäjät",
    "bug-0":"Bugi #{} ei löytynyt",
    "emergency":"Hätätilanne on havaittu tälle botille. Tämä saattaa olla koska joku yrittää päästä sisään minun koodiini.\n\
Jotta voidaan välttää sattumia, Minut oli pakotettu lähtemään kaikilta servuilta heti, missä olin toivoen että ei ole liian myöhäistä.\n\
Lisätietoja tästä hätätilaanteesta mene minun servulleni: https://discord.me/z_bot (Katso linkki dokumentistä jos linkki ei toimi enää: https://zbot.rtfd.io)"
    }

aide={"no-subcmd":"Commandilla `{0.name}`ei ole sub-commandia",
"mods":['Valvoja:','toinen:'],
"footer":"Kirjoita {}help commandi lisätietoja tietystä commandista",
"no-desc-cog":"Ei lisätietoja tästä cog:stä.",
"no-desc-cmd":"Ei lisätietoja tästä commandista.",
"cmd-not-found":"Commandia ei ole nimetty \"{}\"",
"subcmd-not-found":"Tällä commandilla ei ole subcommandia nimetty. \"{}\""}

bvn={"aide":"""__**Tervetuloa liittymis & lähtö viesti moduuliin**__
Tätä moduulia käytetään configuroimaan automaattinen viesti joka kerta kun joku tulee tai lähtee servultasi.
__** Configuraatio**__
`1-` Jotta voit configuroida mihin nämä viestit lähetetään, kirjoita `!config change welcome_channel`lisättynä kanava ID (Right clickkaa -> "Copy ID" tietokoneella,tai jatka painamista kanavaa -> "Copy ID" puhelimelle, mutta sinun pitää ensin ottaa käyttöön Developer muoto jotta saat tämän muodon).
`2-` Jotta voit configuroida viestin, kirjoita  `!config change <welcome|leave> <message>`. Tälle viestille voit käyttää variableja:
 - `{user}` Tägää käyttäjän
 - `{server}` näyttää serverin nimen
 - `{owner}` näyttää serverin omistajan nimen
 - `{member_count}` näyttää tämän hetkisen käyttäjä määrän
"""}

cases={"no-user":"Tämä on mahdotonta löytää tämä käyttäjä. :eyes:",
    "not-found":"Tätä keissiä ei löydetty :confused:",
    "reason-edited":"Syy keissille #{} on vaihdettu!",
    "deleted":"Keissi #{} on poistettu!",
    "cases-0":"{} keissit löydetty: ({}-{})",
    "search-0":"**Käyttäjä:** {U}\n**Muoto:** {T}\n**Valvoja:** {M}\n**Päivämäärä:** {D}\n**Syy:** *{R}*",
    "search-1":"**Käyttäjä:** {U}\n**Serveri:** {G}\n**Muoto:** {T}\n**Valvoja:** {M}\n**Päivämäärä:** {D}\n**Syy:** *{R}*",
    'title-search':'Case #{}',
    'no_database':"Jonkun ajan database alaskäynnin takia, tämä commandi on pois käytöstä"}

events={'mp-adv':"Sinä varmaan yrität kutsua minut tähän servuun? Jos tämä on oikein, en voi liittyä helpolla kutsu linkillä. Adminin täytyy käyttää minun omaa kutsu linkkiä, täällä:<https://bot.discord.io/zbot> :wink:"}

errors={"cooldown":"Olet jäähyllä tältä commandilta :confused: Please wait {} more seconds...",
"badarguments":"Upsis, on mahdotonta muuntaa `{c[3]}` paramittarin\"{c[1]}\" tyyppiä :confused:",
"missingargument":"Upsis, argumentti \"{}\" puuttuu {}",
"membernotfound":"On mahdotonta löytää käyttäjä `{}` :confused:",
"usernotfound":"On mahdotonta löytää käyttäjä `{}` :confused:",
"disabled":"Commandi {} on poissa käytöstä :confused:",
"duration":"Aika `{}` on epäselvä",
"rolenotfound":"On mahdotonta löytää rooli `{0}`",
"invalidcolor":"Väri `{0}` epäselvä"}

find={"user-0":"nimi: {}\nID: {}",
"user-1":"Nimi: {name}\nID: {id}\nPerks: {rangs}\nServers: {servers}\nOwner of: {own}\nLanguages: {lang}\nVoted? {vote}\nXP card: {card}",
"user-2":"Käyttäjää ei löytynyt",
"guild-0":"Serveriä ei löytynyt",
"guild-1":"Nimi: {}\nID: {}\nOmistaja: {} ({})\nKäyttäjät: {} Mukaan lukien {} bottia)\nKieli: {}\nEtuliite (prefix): `{}`",
"chan-0":"kanavaa ei löytynyt",
"chan-1":"Nimi : {}\nID: {}\nServeri: {} ({})",
"help":"Tämä commandi hyväksyy löytämään serverin tai salongin kaikista servereistä missä botti on. Voit myös etsiä Discord käyttäjän tiedot, siltikin vaikka jos hän ei ole minun kanssani serverissä!\
Syntaksi tälle on `!find <user|channel|guild> <ID>`"}

fun={"count-0":"Laskeminen on kesken...",
    "count-1":"Viimeiset {} lähetystä, olet lähettänyt {} viestiä ({}%)",
    "count-2":"Sinä haluat räjäyttää Discordin! {e} Selvien suorituskykyjen syyksi, Minä laitan rajotuksen {l} viestille.",
    "count-3":"Upsis, en pysty lukea tämän kanavan historiaa. Varmista minun luvat asetuksista...",
    "fun-list":"Tässä on lista kaikista käytettävistä hauska commandeista:",
    "no-fun":"Hauska commandit ovat kytketty pois käytöstä tällä serverillä. Näet listan niistä täältä: https://zbot.rtfd.io/en/v3/fun.html",
    "osekour":["Odota, minä olen kohta katsonut elokuvani.","Olemme tulossa! Mutta miksi et vastaa enää? Älä esitä kuollutta!","Kyllä, me tiedämme että siellä on tulipalo, meidän ei tarvitse tulla: Meillä on juhlat palokunnan talossa.","*Pelastus ei ole mahollinen, odota kunnes tämä tauko loppuu, kiitos*","*Tämä numero ei ole olemassa. Yritä uudelleen uudella numerolla.*","*Ylläpito on menossa. Yritä uudelleen 430 tunnin kuluttua.*","*Sinun puheaika on loppunut. Voit ostaa lisää puhe aikaa 86,25 eurolla!*","Kaksi lisää kappaletta Lord of the Ringsissä että olen lukenut tarpeeksi, ja sitten  minulla on aikaa! ","Kiitos että et häirinnyt meitä loman aikana","Anteeksi, täällä on enemmän kuin 3 lumihiutaletta: me olemme jumissa autotallissa","Meidän täytyy odottaa meidän jäähyn loppuun asti... Oletko sanomassa että et tiedä?! On ollut kaksi kuukautta kun aloitimme!"],
    "react-0":"En voinut löytää corresponding viestiä. Sinun täytyy lisätä viesti ID ensimmäiseen argumenttiin, ja emoji toiseen:upside_down:\n Katso myös että voin lukea kanavan viesti historiaa!",
    "thanos":["{0} oli jaettu Thanoksen kanssa","Thanos päätti muuttaa {0} tuhkiin. Ihmiskunnan hyväksi ...."],
    "piece-0":["Kruuna!","Klaava!"],
    "piece-1":"Epäonnistui, se tippu reunaan!",
    "calc-0":"Vastauksessa kestää liian kauan ladata:/",
    "calc-1":"Laskennan ratkaisut `{}` ovat `{}`",
    "calc-2":"Laskennan ratkaisut `{c}` ovat `{l[0]}` and `{l[1]}`",
    "calc-3":"Laskennan ratkaisu `{}` on `{}`",
    "calc-4":"Laskulla `{}` ei ole ratkaisua",
    "calc-5":"Upsis, error tuli: `{}`",
    "no-reaction":"Mahdotonta lisätä reaktioita. Katso minun käyttöoikeudet...",
    "cant-react":"Minulla ei ole tarpeeksi käyttöoikeuksia lisätä reaktioita!",
    "no-emoji":"Mahdotonta löytää tämä emoji!",
    "vote-0":"Sinä voit laittaa enemmän kuin 20 vaihtoehtoa, ja myös vähemmän negatiivisiä!",
    "blame-0":"Lista kaikista käytettävistä nimistä**{}**:lle",
    "no-database":"As our database is offline, access to fun commands is restricted to people with permission \"Manage Server\"",
    "no-embed-perm":"Minulla ei ole käyttöoikeuksia \"Embed links\" :confused:",
    "embed-error":"Error havaittu: `{}`",
    "invalid-city":"Pätemätön kaupunki :confused:",
    "no-roll":"Ei vaihtoehtoa löydetty"
    }

infos={"text-0":"""Moi! Olen {0} !
Olen robotti joka voi tehä monia asioita: Valvontaa, pieniä pelejä, taso systeemi, tilastoja, ja monia muita hyödyttäviä commandeja (ja myös täysin turhia)! 
Voit aloittaa viestittämällä `!help` tällä kanavalla niin näet kaikki käytettävissä olevat commandit, sitten `!config see` aikoo näyttää configuraatio muodot (nettisivua ollaan tekemässä). 
Kaikki jotka auttoivat minun tekeimsessä, minun omistaja ja minä haluamme kiittää Adri526, Awhikax, Jees1 (tämän kielen kääntäjä) ja Aragorn1202! Iso kiitos heille.
:globe_with_meridians: Some links may be useful: 
:arrow_forward: Minun Discord palvelin: : http://discord.gg/N55zY88
:arrow_forward: Linkki kutsua minut toiselle palvelimelle : <https://bot.discord.io/zbot>
:arrow_forward: Bot documentti : <https://zbot.rtfd.io/>
:arrow_forward: Minun tekijän Twitteri : <https://twitter.com/z_runnerr>
 Hyvää päivän jatkoa!""",
"docs":"Tässä on linkki botin documenttiin:",
"stats-title":"**Bot tilastot**",
"stats":"""**Bot versio:** {bot_v} \n**Kaikkien palvelimien numero missä olen:** {s_count} \n**Numero kaikista näkyvistä jäsenistä:** {m_count} ({b_count} **botit**)\n**Numero koodi riveistä:** {l_count}\n**Käytettyjä kieliä:** {lang}\n** {p_v} \n**Versio `discord.py`stä:** {d_v} \n**Ladataan RAMia:** {ram} GB \n**Ladataan CPU:ssa:** {cpu} % \n**API viive aika:** {api} ms\n**Kaikki xp kerätty:** {xp}""",
"admins-list":"Adminit tälle botille ovat : {}",
"prefix":"Lista kaikista käytettävissä olevista etuliitoista:"}

infos_2={"membercount-0":"Numero jäsenistä",
"membercount-1":"Numero boteista",
"membercount-2":"Numero ihmisistä",
"membercount-3":"Numero online jäsenistä",
"fish-1":"Numero kaloista"}

keywords={"depuis":"since",
          "nom":"name",
          "online":"online",
          "idle":"idle",
          "dnd":"do not disturb",
          "offline":"offline",
          "oui":"yes",
          "non":"no",
          "none":"none",
          "low":"low",
          "medium":"medium",
          "high":"high",
          "extreme":"extreme",
          "aucune":"none",
          "membres":"members",
          "subcmds":"subcommands",
          "ghost":"Ghost"
          }

kill={"list":["Oh you, you gonna to die!",
          "***BOUM !*** {1} fell into a trap posed by {0} !",
          "Luckily, the ground has cushioned the fall of {1} !",
          "{0} shouted \"Fus Roh Dah\" while {1} was next to a cliff...",
          "No, you can't stop bullets with your hands {1} :shrug:",
          "You have to be __in__ the elevator {1}, not __above__...",
          "{1} stayed too close to the speakers during a heavy metal concert.",
          "Staying within 10 meters of an atomic explosion wasn't a good idea {1}...",
          "No ! Double jumps are not possible {1} !",
          "{1} imitated Icare... splash.",
          "It's nice to have a portal gun {1}, but don't open portals above spades...",
          "{1} died. Peace to his soul... :sneezing_face:",
          "{0} killed {1}",
          "{1} was shot by {0}",
          "Bye {1} ! :ghost:",
          "{1} saw a flying anvil fall... on his head :head_bandage:",
          "{1} commit suicide after {0} has cut his connection",
          "Caution {1} ! Fire burns :fire:",
          "{1} fought zombies without shovel",
          "{1} tried to hug a creeper",
          "{1}, lava baths are hot, but lava burns...",
          "{1} tried a rocket jump",
          "You shouldn't listen to the pretty melody of the Lullaby, {1} :musical_note:",
          "{2}.exe *has stopped working*"
          ]}

logs={"slowmode-enabled":"Slowmode enabled in {channel} ({seconds}s)",
"slowmode-disabled":"Slowmode disabled in {channel}",
"clear":"{number} deleted messages in {channel}",
"kick":"{member} has been kicked (reason: {reason} | case #{case})",
"ban":"{member} has been banned (reason: {reason} | case #{case})",
"unban":"{member} is no more banned (reason: {reason})",
"mute-on":"{member} is now muted (reason : {reason} | case #{case})",
"mute-off":"{member} is no more muted",
"softban":"{member} has been 'softbanned' (reason: {reason} | case #{case})",
"warn":"{member} has been warned: {reason} (case #{case})",
"tempmute-on":"{member} is now muted for {duration} (reason : {reason} | case #{case})",
"d-autounmute":"automatic unmute",
"d-unmute":"unmuted by {}",
"d-invite":"Automod (Discord invite)",
"d-young":"Automod (too recent account)",
"d-gived_roles":"Automated action (config gived_roles)",
"d-memberchan":"Automated action (config membercount)"}

mc={"contact-mail":"If you notice an error in the information provided, please contact me personally, or report the error directly [on the site](https://fr-minecraft.net).",
    "serv-title":"Server information {}",
    "serv-0":"Number of players",
    "serv-1":"List of the first 20 players connected",
    "serv-2":"List of online players",
    "serv-3":"Latency",
    "serv-error":"Oops, an unknown error occurred. Please try again later :confused:",
    "no-api":"Error: Unable to connect to API",
    "no-ping":"Error: Unable to ping this server",
    "success-add":"A message with server details {} has been added to the channel {} !",
    "cant-embed":"Cannot send embed. Please make sure the \"Embed links\" permission is enabled.",
    "names":("Block","Entity","Item","Command","Advancement"),
    "entity-help":"This command allows you to obtain information about any Minecraft entity. You can give its full or partial name, in French or English, or even its identifier. Just enter `!mc entity <name>`",
    "block-help":"This command allows you to obtain information on any Minecraft block. You can give its full or partial name, in French or English, or even its identifier. Just enter `!mc block <name>`",
    "item-help":"This command allows you to obtain information on any Minecraft item. You can give its full or partial name, in French or English, or even its identifier. Just enter `!mc item <name>`",
    "cmd-help":"This command allows you to obtain information about any Minecraft command. All you have to do is type `!mc entity <nom>`",
    "adv-help":"This command provides information about any advancement of the game Minecraft. Simply enter the name or the identifier of the advancement.",
    "no-entity":"Unable to find this entity",
    "no-block":"Unable to find this block",
    "no-item":"Unable to find this item",
    "no-cmd":"Unable to find this command",
    "no-adv":"Unable to find this advancement",
    "mojang_desc":{'minecraft.net':'Official Site',
      'session.minecraft.net':'Multiplayer sessions (obsolete)',
      'account.mojang.com':'Mojang account management site',
      'authserver.mojang.com': "Authentication server",
      'sessionserver.mojang.com':'Multiplayer sessions',
      'api.mojang.com': "API service provided by Mojang",
      'textures.minecraft.net':'Texture server (skin & capes)',
      'mojang.com':'Official website'},
    "dimensions":"Width: {d[0]}\nLength: {d[1]}\nHeight: {d[2]}",
    "entity-fields":('ID','Type','Health Points','Attack Points','Experience Points Released to Death','Preferred Biomes','Added in the version'),
    "block-fields":("ID","Stack size","Creative mod tab","Damage points","Durability","Tool able to destroy it","Mobs able to loot it","Added in the version"),
    "item-fields":('ID',"Size of a stack",'Creative mode tab','Damage points',"Durability points","Tool able to destroy it","Mobs able to drop this item","Added in the version"),
    "cmd-fields":("Name","Syntax","Examples","Added in the version"),
    "adv-fields":("Name","ID","Type","Action","Parent","Children","Added in the version"),
      }

modo={"slowmode-0":"The slowmode is now disabled in this channel.",
    "slowmode-1":"Impossible to set a frequency higher than two minutes",
    "slowmode-2":"The {} channel is now in slowmode. Wait {} seconds before sending a message.",
    "slowmode-3":"This value is invalid",
    "slowmode-info":"The slowmode of this channel is currently at {} seconds",
    "cant-slowmode":"Oops, I don't have permission to `Manage this channel` :confused:",
    "clear-0":"{} messages deleted!",
    "need-manage-messages":"Permission \"Manage Messages\" missing :confused:",
    "need-read-history":"Oops, I'm missing the permission to \"Read Message History\" :confused: ",
    "clear-1":"I can't delete so few messages",
    "clear-nt-found":"Hmm... impossible to delete these messages. Discord tells me they don't exist :thinking:",
    "cant-kick":"Permission 'Kick members' needed :confused:",
    "kick":"Member {} has been kick from this server for the reason `{}`",
    "staff-kick":"You can't kick another staff!",
    "kick-noreason":"You have just been expelled from the server {} :confused:",
    "kick-reason":"You have just been expelled from the server {} :confused:\nReason : {}",
    "kick-1":"It seems that this member is too high for me to kick him out :thinking:",
    "error":"Oops, an unknown error occurred. Try again later or contact support",
    "warn-mp":"You have received a warning from the *{}* server: \n{}",
    "staff-warn":"You can't warn another staff member!",
    "warn-1":"The member `{}` has been warned for the reason `{}`",
    "warn-bot":"I can't warn a bot ^^",
    "warn-but-db":"Our database being offline, the warning could not be saved. Nevertheless, the member did receive his warning in DM",
    "staff-mute":"You can't prevent another staff member from speaking ",
    "mute-1":"The member {} has been silenced for the reason `{}`!",
    "mute-created":"Successfully created `muted` role!",
    "no-mute":"Oops, it seems that the role `muted` does not exist :confused: Please create it and assign permissions manually.",
    "cant-mute":"Oops, it seems that I don't have enough permissions for that.... Please give me permission `Manage roles` before continuing.",
    "mute-high":"Oops, it seems that the `muted` role is too high for me to give it... Please fix this problem by placing my role higher than the `muted` role.",
    "already-mute":"This member is already mute!",
    "already-unmute":"This member isn't muted!",
    "unmute-1":"The member {} can now speak again.",
    "cant-ban":"Permission 'Ban members' needed :confused:",
    "staff-ban":"You can't ban another staff!",
    "ban-noreason":"You have just been banned from the server {} :confused:",
    "ban-reason":"You have just been banned from the server {} :confused:\nReason : {}",
    "ban":"Member {} has been banned from this server for the reason `{}`",
    "ban-1":"It seems that this member is too high for me to ban him. :thinking:",
    "ban-list-title-0":"List of banned members of the server '{}'",
    "ban-list-title-1":"List of 45 banned members of the server '{}'",
    "ban-list-title-2":"List of 60 banned members of the server '{}'",
    "ban-list-error":"Oops, it looks like there are too many users to display :confused:",
    "no-bans":"No member seems to be banned from here",
    "unban":"The member {} is no longer banned from this server",
    "cant-find-user":"Oops, no way to find the user **{}**",
    "ban-user-here":"This person is not part of the banned members list :upside_down:",
    "caps-lock":"Hey {}, beware of caps lock!",
    "wrong-guild":"Oops, it seems this emoji doesn't belong to this server :thinking:",
    "cant-emoji":"Oops, I'm missing the permission `Manage emojis` :confused:",
    "emoji-valid":"The emoji {} has been modified to allow only the roles `{}`",
    "emoji-renamed":"The emoji {} has been renamed!",
    "cant-pin":"Oops, I don't have permission to pin messages",
    "pin-error":"Oops, I can't find that message (Error : `{}`)",
    "pin-error-3":"Oops, impossible to pin this message (do you have more than 50 pinned messages?). Error : `{}`",
    "react-clear":"I'm unable to find this message :confused:",
    "em-list":"{} (`:{}:`) added on {} {}",
    "em-private":"[Restricted]",
    "em-list-title":"Emojis of the server {}",
    "tempmute-1":"The member {} has been silenced for the reason `{}`, for {}!",
    "role-high":"Oops, this role is too high for me to change. Please move my role above the role `{}` before trying again :confused:"
    }

morpion={'user-begin':'{}, you begin!',
        'bot-begin':"Let's go, I'll start!",
        'tip':"\n*To play, simply type a number between 1 and 9, corresponding to the chosen case. I play the red, you play the blue*",
        'nul':"Draw, no one won...",
        'too-late':"You took too long to decide. Game over!",
        'pion-1':"There's already a pawn on that cell!",
        'pion-2':'Invalid input case',
        'win-1':"Well done, {} won!",
        'win-2':"I won! End of the game!"}

perms={"perms-0":"Member/role {} not found",
        "perms-1":"**'{}' permissions:**\n\n"
       }

rss={"yt-help":"To search for a youtube channel, you must enter the channel ID. You will find it at the end of the string url, it can be either the name, or a string of random characters. \
*Tip: some channels are already filled in my code. Sometimes you can just put `neil3000` or `Oxisius`* :wink:",
"tw-help":"To search for a twitter channel, you must enter the identifier of that channel. You will find it at the end of the string url, it usually corresponds to the user's name. \
For example, for %https://twitter.com/Mc_AsiliS*, you must enter `Mc_AsiliS`.",
"web-help":"To search for an rss feed from any website, simply enter the rss/atom feed url as a parameter. If the feed is valid, I will send you the last article posted on this site. \
*Tip: some rss feeds are already filled in my code. Sometimes you can just put `fr-minecraft` or `minecraft.net`* :wink:",
"web-invalid":"Oops, this url address is invalid :confused:",
"nothing":"I found nothing on this search :confused:",
"success-add":"The rss feed of type '{}' with link <{}> has been properly added in the channel {} !",
"invalid-link":"Oops, this url address is invalid or incomplete :confused:",
"fail-add":"An error occurred while processing your response. Please try again later, or contact bot support (enter the command `about` for server link)",
"flow-limit":"For performance reasons, you cannot track more than {} rss feeds per server.",
"yt-form-last":"""{logo}  | Here is the last video of {author}:
{title}
Published on {date}
Link : {url}
""",
"tw-form-last":"""{logo}  |  Here is the last tweet of {author}:
Written on {date}
{title}
Link : {url}
""",
"twitch-form-last":"""{logo}  | Here is the last video of {author}:
{title}
Published on {date}
Link : {url}
""",
"web-form-last":"""{logo}  |  Here is the last post of {author}:
**{title}**
*Written on {date}*
Link : {link}""",
"yt-default-flow":"{logo}  | New video of {author}: **{title}**\nPublished on {date}\nLink : {link}\n{mentions}",
"tw-default-flow":"{logo}  | New tweet of {author}! ({date})\n\n{title}\n\nLink: {link}\n\n{mentions}",
"twitch-default-flow":"{logo}  | New live by {author}! ({date})\n\n{title}\n\nLink: {link}\n\n{mentions}",
"web-default-flow":"{logo}  | New post on {author} ({date}) :\n    {title}\n\n{link}\n\n{mentions}",
"list":"*Type the number of the flow to modify*\n\n**Link - Type - Channel - Mentions**\n",
"list2":"*Type the number of the flow to delete*\n\n**Link - Type - Channel**\n",
'tw':'Twitter',
'yt':'YouTube',
'twitch':'Twitch',
'web':'Web',
'mc':'Minecraft',
'choose-mentions-1':"Please choose the flow to modify",
"choose-delete":"Please choose the flow to delete",
"too-long":"You waited too long, sorry :hourglass:",
"no-roles":"No role has been configured yet.",
"roles-list":"Here is the list of roles already indicated: {}",
"choose-roles":"What roles will be mentioned?",
"not-a-role":"The role `{}` is not found. Try again:",
"roles-0":"This feed has been modified to mention the roles {}",
"roles-1":"This feed has been modified to not mention any role",
"no-feed":"Oops, you don't have any rss feeds to manage!",
"delete-success":"The flow has been successfully deleted!",
"no-db":"As the database is currently offline, this feature is temporarily disabled :confused:",
"guild-complete":"{} rss streams have been correctly reloaded, in {} seconds!",
"guild-error":"An error occurred during the procedure: `{}`\nIf you think this error is not your own, you can report it to support",
"guild-loading":"Reloading {}",
"move-success":"The rss feed #{} has been moved in the channel {}!",
"change-txt":"""The current message contains  \n```\n{text}\n```\nPlease enter the text to be used when creating a new post. You can use several variables, of which here is the list:
- `{author}`: the author of the post
- `{channel}`: the Discord channel in which the message is posted
- `{date}`: the post date (UTC)
- `{link}` or `{url}`: a link to the post
- `{logo}`: an emoji representing the type of post (web, Twitter, YouTube...)
- `{mentions}`: the list of mentioned roles
- `{title}`: the title of the post""",
"text-success":"The text of the feed #{} has been modified!\n New text : \n```\n{}\n```",
"invalid-flow":"This url is invalid (empty or inaccessible rss flow) :confused:",
"research-timeout":"The web page took too long to answer, I had to interrupt the process :eyes:"
}

server={"config-help": "This command is mainly used to configure your server. By doing `!config see [option]` you will get \
an overview of the current configurations, and server administrators can enter `!config change <option> role1, role2, role3...` \
to modify a configuration, or `!config del <option>` to reset the option (`!config change <option>` works the same way).\nThe list of available options is available at <https://zbot.rtfd.io/en/latest/config.html#list-of-every-option>",
        "change-0": "This option does not exist :confused:",
        "change-1": "Oops, an internal error occurred...",
        "change-2": "The '{}' option value has been deleted",
        "change-3": "The role '{}' was not found :confused: (Check upper case and special characters)",
        "change-4": "The '{}' option expects a boolean (True/False) parameter in value :innocent:",
        "change-5": "The channel '{}' was not found :confused: (Enter the exact mention, name or identifier of the channel(s)",
        "change-6": "The '{}' option expects a number in parameter :innocent:",
        "change-7": "This language is not available. Here is the list of currently supported languages: {}",
        "change-8": "This level does not exist. Here is the list of the levels currently available: {}",
        "change-9": "The emoji `{}` was not found",
        "change-role": "The '{}' option has been modified with the following roles: {}",
        "change-bool": "The '{}' option has been modified with the value *{}*",
        "change-textchan": "The '{}' option has been modified with the channels {}",
        "change-text": "The option '{}' has been replaced by the following text: \n```\n{}\n```",
        "change-prefix":"The prefix has been successfully replaced by `{}`",
        "change-lang": "The bot language is now in `{}`",
        "change-raid":"The anti-raid security level is now set to **{}** ({})",
        "change-emojis":"The emotions for the option '{}' are now {}",
        "new_server": "Your server has just been registered for the first time in our database. Congratulations :tada:",
        "see-0":"Enter `!config help` for more details",
        "see-1":"{} server configuration",
        "change-prefix-1":"This prefix is too long to be used!",
        "wrong-prefix":"Oops, it seems this prefix is invalid :thinking: If the problem persists, please choose another one",
        "opt_title":"Option '{}' of server {}",
        "not-found":"The server {} has not yet been registered in the database"
    }

server_desc={"prefix":"Current bot prefix: {}",
            "language": "Current bot language for this server: **{}**",
            "clear": "List of roles that can use the 'clear' command: {}",
            "slowmode": "List of roles that can use 'slowmode' and 'freeze' commands: {}",
            "mute": "List of roles that can use the 'mute' command: {}",
            "kick": "List of roles that can use the 'kick' command: {}",
            "ban": "List of roles that can use the command 'ban': {}",
            "warn": "List of roles that can use commands 'warn' and 'cases': {}",
            "say": "List of roles that can use the command 'say' : {}",
            "hunter": "List of all chat rooms in which the game *Hunter* is active: {}",
            "welcome_channel": "List of channels where to send welcome/leave messages: {}",
            "welcome": "Message sent when a member arrives: {}",
            "leave": "Message sent when a member leaves: {}",
            "gived_roles": "List of roles automatically given to new members: {}",
            "bot_news": "List of channels where to send bot news: {}",
            "modlogs_channel":"Channel where to send moderation logs: {}",
            "save_roles": "Should roles be saved when a member leaves, in case he returns? {}",
            "poll_channels": "List of channels where :thumbsup: and :thumbsdown: reactions will be automatically added to each message : {}",
            "enable_xp": "Should the xp system be enabled? {}",
            "levelup_msg":"Message sent when a member earns an xp level: {}",
            "anti_caps_lock": "Should the bot send a message when a member sends too many capital letters? {}",
            "enable_fun": "Are the commands listed in the `!fun` command enabled? {}",
            "membercounter":"Channel displaying number of members in its name: {}",
            "anti_raid":"Level of anti-raid protection: {} \n*([Documentation](https://zbot.rtfd.io/en/latest/moderator.html#anti-raid))*",
            "vote_emojis":"Emojis used for poll reactions: {}",
            "help_in_dm":"Send help message in Private Message? {}",
            "muted_role":"Used role to mute members : {}"}

stats_infos={"not-found":"Unable to find {N}",
            "member-0":"Nickname",
            "member-1":"Created at",
            "member-2":"Joined at",
            "member-3":"Arrival position",
            "member-4":"Status",
            "member-5":"Activity",
            "member-6":"Administrator",
            "role-0":"ID",
            "role-1":"Color",
            "role-2":"Mentionable",
            "role-3":"Number of members",
            "role-4":"Displayed separately",
            "role-5":"Hierarchical position",
             "role-6":"Unique member with this role",
            "user-0":"On this server?",
            "emoji-0":"Animated",
            "emoji-1":"Managed by Twitch",
            "emoji-2":"String (for bots)",
            "emoji-3":"Server which own it",
            "textchan-0":"Category",
            "textchan-1":"Description",
            "textchan-2":"NSFW",
            "textchan-3":"Number of webhooks",
            "textchan-4":":warning: Missing permissions !",
            "textchan-5":"Channel",
            "voicechan-0":"Vocal channel",
            "guild-0":"Guild",
            "guild-1":"Owner",
            "guild-2":"Region",
            "guild-3":"Text : {} | Vocal : {} ({} categories)",
            "guild-4":"Online members",
            "guild-5":"Number of emojis",
            "guild-6":"Number of channels",
            "guild-7":"{} including {} bots ({} connected)",
            "guild-8":"Two-factor authentification",
            "guild-9":"Security level",
            "guild-10":"Time before being AFK",
            "guild-11.1":"20 first roles (total {})",
            "guild-11.2":"Roles list (total {})",
            "guild-12":"Number of invites",
            "inv-0":"URL link",
            "inv-1":"Inviter",
            "inv-2":"Uses",
            "inv-3":"Time left",
            "inv-4":"Invite",
            "inv-5":"If information seems missing, it is unfortunately because Discord did not communicate it",
            "categ-0":"Category",
            "categ-1":"Position",
            "categ-2":"Text : {} | Vocal : {}",
             }

users = {'invalid-card':'This style is invalid. Here is the list of styles you can use: {}',
        'missing-attach-files':'Oops, I\'m missing the permission to Attach Files :confused:',
        'changed-0':'Your xp card now uses the style {}',
        'changed-1':'Oops, an internal error occurred during the processing of the request. Try again later or contact support.',
        'card-desc':"Here is an example of your xp card. You can enter the command `profile card <style>` to change the style\n*Your xp card will only refresh when you have won xp*"}

xp = {'card-level':'LEVEL',
        'card-rank':'RANK',
        '1-no-xp':"You don't have any xp yet!",
        '2-no-xp':"This member does not have any xp!",
        "del-user":"<deleted user>",
        "low-page":"I cannot display a negative page number!",
        "high-page":"There are not that many pages!",
        "top-title-1":"Global ranking",
        "top-name":"__Top {}-{} (page {}/{}):__",
        "default_levelup":"Hey, {user} has just reached **level {level}**! Keep this way!",
        "top-your":"Your rank"}
