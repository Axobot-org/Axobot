#!/usr/bin/env python
#coding=utf-8

current_lang = {'current':'fi'}

activity={"rien":"Ei mitään",
        "play":"soittaa",
        "stream":"striimaa",
        "listen":"listening to",
        "watch":"katsoo"
        }

admin={
        "change_game-0":"Valitse *play*, *watch*, *listen* tai *stream* seurattu nimellä",
        "msg_2-0":"Operaatio käynnissä...",
        "msg_2-1":"Ei vaikuttavia käyttäjiä",
        "msg_2-2":"1 vaikuttanut käyttäjä",
        "msg_2-3":"vaikutetut käyttäjät",
        "bug-0":"Bugi #{} ei löytynyt",
        "emergency":"Hätätilanne on havaittu tälle botille. Tämä saattaa olla koska joku yrittää päästä sisään minun koodiini.\n\
Jotta voidaan välttää sattumia, Minut oli pakotettu lähtemään kaikilta servuilta heti, missä olin toivoen että ei ole liian myöhäistä.\n\
Lisätietoja tästä hätätilaanteesta mene minun servulleni: https://discord.me/z_bot (Katso linkki dokumenttiin jos linkki ei toimi enää: https://zbot.rtfd.io)"
        }

aide={"no-subcmd":"komenolla `{0.name}`ei ole toissijaista komentoa",
        "mods":['Valvoja:','toinen:'],
        "footer":"Viestitä {}help komento niin saat lisätietoja tietyistä komennoista",
        "no-desc-cog":"Ei lisätietoja tästä cog:stä.",
        "no-desc-cmd":"Ei lisätietoja tästä komennosta.",
        "cmd-not-found":"Komentoa  \"{}\" ei ole nimetty",
        "subcmd-not-found":"Tällä komennolla ei ole toissijaista komentoa nimetty. \"{}\""
        }

bvn={"aide":"""__**Tervetuloa liittymis & lähtö viesti moduuliin**__
Tätä moduulia käytetään konfiguroimaan automaattinen viesti joka kerta kun joku tulee tai lähtee servultasi.
__** Konfiguraatio**__
`1-` Jotta voit konfiguroida mihin nämä viestit lähetetään, kirjoita `!config change welcome_channel`lisättynä kanava tunniste (Right klikkaa -> "Copy ID" tietokoneella,tai jatka painamista kanavaa -> "Kopioi tunniste" puhelimelle, mutta sinun pitää ensin ottaa käyttöön Developer muoto jotta saat tämän muodon).
`2-` Jotta voit konfiguroida viestin, kirjoita  `!config change <welcome|leave> <message>`. Tälle viestille voit käyttää variableja:
 - `{user}` Tägää käyttäjän
 - `{server}` näyttää serverin nimen
 - `{owner}` näyttää serverin omistajan nimen
 - `{member_count}` näyttää tämänhetkisen käyttäjämäärän
"""}

cases={"no-user":"Tämä on mahdotonta löytää tämä käyttäjä. :eyes:",
        "not-found":"Tätä keissiä ei löydetty :confused:",
        "reason-edited":"Syy keissille #{} on vaihdettu!",
        "deleted":"Keissi #{} on poistettu!",
        "cases-0":"{} keissit löydetty: ({}-{})",
        "search-0":"**Käyttäjä:** {U}\n**Muoto:** {T}\n**Valvoja:** {M}\n**Päivämäärä:** {D}\n**Syy:** *{R}*",
        "search-1":"**Käyttäjä:** {U}\n**Serveri:** {G}\n**Muoto:** {T}\n**Valvoja:** {M}\n**Päivämäärä:** {D}\n**Syy:** *{R}*",
        'title-search':'Case #{}',
        'no_database':"Jonkun ajan database alas käynnin takia, tämä komento on pois käytöstä"}

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
        "help":"Tämä komento hyväksyy löytämään serverin tai salongin kaikista servereistä missä botti on. Voit myös etsiä Discord käyttäjän tiedot, siltikin vaikka jos hän ei ole minun kanssani serverissä!\
Syntaksi tälle on `!find <user|channel|guild> <ID>`",
        "role-0":"Role not found",
        "role-1":"Name: {}\nID: {}\nGuild: {} ({})\nMembers number: {}\nColour: {}"}

fun={"count-0":"Laskeminen on kesken...",
        "count-1":"Viimeiset {} lähetystä, olet lähettänyt {} viestiä ({}%)",
        "count-2":"Sinä haluat räjäyttää Discordin! {e} Selvien suorituskykyjen syyksi, Minä laitan rajotuksen {l} viestille.",
        "count-3":"Upsis, en pysty lukea tämän kanavan historiaa. Varmista minun luvat asetuksista...",
        "fun-list":"Tässä on lista kaikista käytettävistä hauska komentoista:",
        "no-fun":"Hauska komennot ovat kytketty pois käytöstä tällä serverillä. Näet listan niistä täältä: https://zbot.rtfd.io/en/v3/fun.html",
        "osekour":["Odota, minä olen kohta katsonut elokuvani.","Olemme tulossa! Mutta miksi et vastaa enää? Älä esitä kuollutta!","Kyllä, me tiedämme että siellä on tulipalo, meidän ei tarvitse tulla: Meillä on juhlat palokunnan talossa.","*Pelastus ei ole mahollinen, odota kunnes tämä tauko loppuu, kiitos*","*Tämä numero ei ole olemassa. Yritä uudelleen uudella numerolla.*","*Ylläpito on menossa. Yritä uudelleen 430 tunnin kuluttua.*","*Sinun puheaika on loppunut. Voit ostaa lisää puhe aikaa 86,25 eurolla!*","Kaksi lisää kappaletta Lord of the Ringsissä että olen lukenut tarpeeksi, ja sitten  minulla on aikaa! ","Kiitos että et häirinnyt meitä loman aikana","Anteeksi, täällä on enemmän kuin 3 lumihiutaletta: me olemme jumissa autotallissa","Meidän täytyy odottaa meidän jäähyn loppuun asti... Oletko sanomassa että et tiedä?! On ollut kaksi kuukautta kun aloitimme!"],
        "react-0":"En voinut löytää corresponding viestiä. Sinun täytyy lisätä viesti ID ensimmäiseen argumenttiin, ja emoji toiseen:upside_down:\n Katso myös että voin lukea kanavan viesti historiaa!",
        "thanos":["{0} oli jaettu Thanoksen kanssa","Thanos päätti muuttaa {0} tuhkiin. Ihmiskunnan hyväksi ...."],
        "piece-0":["Kruuna!","Klaava!"],
        "piece-1":"Epäonnistui, se tippu reunaan!",
        "cookie":"{} offered a box of cookies to <@375598088850505728>! {}",
        "calc-0":"Vastauksessa kestää liian kauan ladata:/",
        "calc-1":"Laskennan ratkaisut `{}` ovat `{}`",
        "calc-2":"Laskennan ratkaisut `{c}` ovat `{l[0]}` and `{l[1]}`",
        "calc-3":"Laskennan ratkaisu `{}` on `{}`",
        "calc-4":"Laskulla `{}` ei ole ratkaisua",
        "calc-5":"Upsis, virhe tuli: `{}`",
        "no-reaction":"Mahdotonta lisätä reaktioita. Katso minun käyttöoikeudet...",
        "cant-react":"Minulla ei ole tarpeeksi käyttöoikeuksia lisätä reaktioita!",
        "no-emoji":"Mahdotonta löytää tämä emoji!",
        "vote-0":"Sinä voit laittaa enemmän kuin 20 vaihtoehtoa, ja myös vähemmän negatiivisia!",
        "blame-0":"Lista kaikista käytettävistä nimistä**{}**:lle",
        "no-database":"As our database is offline, access to fun commands is restricted to people with permission \"Manage Server\"",
        "no-embed-perm":"Minulla ei ole käyttöoikeuksia \"Embed links\" :confused:",
        "embed-error":"Virhe havaittu: `{}`",
        "invalid-city":"Pätemätön kaupunki :confused:",
        "uninhabited-city":"Uninhabited city :confused:",
        "no-roll":"Ei vaihtoehtoa löydetty",
        'no-say':"En voi lähettää viestiä tälle kanavalle",
        'no-voicechan':'You must be in a vocal channel in order to use this command.',
        'cant-stream':"Warning: You don't have enough permissions to make a video chat (Permission \"Stream\").",
        "afk-no-perm":"Oops, I cannot change your nickname :confused:",
        "afk-user-1":"This member is AFK, because {}",
        "afk-user-2":"This user is AFK!",
        "afk-done":"You are now AFK",
        "unafk-done":"You aren't anymore AFK"
        }

infos={"text-0":"""Moi! Olen {0} !
Olen robotti joka voi tehdä monia asioita: Valvontaa, pieniä pelejä, taso systeemi, tilastoja, ja monia muita hyödyttäviä komentoja (ja myös täysin turhia)! 
Voit aloittaa viestittämällä `!help` tällä kanavalla niin näet kaikki käytettävissä olevat komennot, sitten `!config see` aikoo näyttää konfiguraatio muodot (nettisivua ollaan tekemässä). 
Kaikki jotka auttoivat minun tekeimsessä, minun omistaja ja minä haluamme kiittää Adri526, Awhikax, Jees1 (tämän kielen kääntäjä) ja Aragorn1202! Iso kiitos heille.
:globe_with_meridians: Jotain linkkejä jotka voivat auttaa: 
:arrow_forward: Minun Discord palvelin: : http://discord.gg/N55zY88
:arrow_forward: Linkki kutsua minut toiselle palvelimelle : <https://bot.discord.io/zbot>
:arrow_forward: Bot dokumentti : <https://zbot.rtfd.io/>
:arrow_forward: Minun tekijän Twitter : <https://twitter.com/z_runnerr>
 Hyvää päivän jatkoa!""",
        "docs":"Tässä on linkki botin dokumenttiin:",
        "stats-title":"**Bot tilastot**",
        "stats":"""**Bot versio:** {bot_v} \n**Kaikkien palvelimien numero missä olen:** {s_count} \n**Numero kaikista näkyvistä jäsenistä:** {m_count} ({b_count} **botit**)\n**Numero koodi riveistä:** {l_count}\n**Käytettyjä kieliä:** {lang}\n** {p_v} \n**Versio `discord.py`stä:** {d_v} \n**Ladataan RAMia:** {ram} GB \n**Ladataan CPU:ssa:** {cpu} % \n**API viive aika:** {api} ms\n**Kaikki xp kerätty:** {xp}""",
        "admins-list":"Adminit tälle botille ovat : {}",
        "prefix":"Lista kaikista käytettävissä olevista etuliitoista:",
        'discordlinks':{'Servers status':'https://dis.gd/status',
                'Discord ToS':'https://dis.gd/tos',
                'Report a bug/ a user':'https://dis.gd/report',
                'Suggest something to Discord':'https://dis.gd/feedback',
                'Selfbots article':'https://support.discordapp.com/hc/articles/115002192352',
                'ToS for bot devs':'https://discordapp.com/developers/docs/legal'},}

infos_2={"membercount-0":"Numero jäsenistä",
"membercount-1":"Numero boteista",
"membercount-2":"Numero ihmisistä",
"membercount-3":"Numero paikalla olevista jäsenistä",
"fish-1":"Numero kaloista"}

keywords={"depuis":"asti",
          "nom":"nimi",
          "online":"paikalla",
          "idle":"toimeton",
          "dnd":"älä häiritse",
          "offline":"offline tilassa",
          "oui":"kyllä",
          "non":"ei",
          "none":"ei yhtään",
          "low":"alhainen",
          "medium":"keskikokoinen",
          "high":"ylhäinen",
          "extreme":"äärimmäinen",
          "aucune":"ei yhtään",
          "membres":"members",
          "subcmds":"Toissijainen komento",
          "ghost":"Haamu",
          "unknown":"Tuntematon"
          }

kill={"list":["Jaahas, olet kuolemassa!",
          "***PUM !*** {1} tippui ansaan, {0} viritti ansan !",
          "Onneksi, maa oli pehmustettu tippumisen käyttäjältä {1} !",
          "{0} Huusi \"Fus Roh Dah\" kun {1} oli kallion vieressä...",
          "Et voi pysäyttää panoksia käsilläsi, {1}. :shrug:",
          "Sinun pitää olla hissin __sisällä__, {1}. Ei __yläpuolella__...",
          "{1} oli liian lähellä kaijuttimia monster rokki konsertissa.",
          "Staying within 10 meters of an atomic explosion wasn't a good idea {1}...",
          "Eii ! Tupla hypyt ei ole mahdollisia, {1} !",
          "{1} imitated Icare... splash.",
          "It's nice to have a portal gun {1}, but don't open portals above spades...",
          "{1} died. Peace to his soul... :sneezing_face:",
          "{0} tappoi {1}",
          "{0} ampui käyttäjän {1}",
          "Heippa {1} ! :ghost:",
          "{1} näki alsin putouksen... hänen päähän päin :head_bandage:",
          "{1} commit suicide after {0} has cut his connection",
          "Huomio {1} ! Tuli palaa :fire:",
          "{1} tappeli zombeja ilman lapiota",
          "{1} yritti halata creepperiä",
          "{1}, laava kylvyt on kuumia mutta, laava palaa...",
          "{1} tried a rocket jump",
          "Sinun ei kannattaisi kuunnella söpöä melodiaa keholaulusta, {1} :musical_note:",
          "{2}.exe *On lakannut toimimasta*"
          ]}

logs={"slowmode-enabled":"Hidastusmuoto on kytketty päälle kanavalla {channel} ({seconds}s)",
"slowmode-disabled":"Hidastusmuoto on kytketty pois kanavalla {channel}",
"clear":"{number} viestiä poistettu kanavalla {channel}",
"kick":"{member} on potkittu (syyllä: {reason} | tapaus #{case})",
"ban":"Käyttäjälle {member} on annettu porttikielto (syyllä: {reason} | keissi #{case})",
"unban":"Käyttäjällä {member} ei ole enään porttikieltoa (syy: {reason})",
"mute-on":"{member} on nyt mykistetty (syy : {reason} | tapaus #{case})",
"mute-off":"{member} ei ole enään mykistetty",
"softban":"{member} on väliäikaisesti potkittu (syy: {reason} | tapaus #{case})",
"warn":"{member} on varoitettu: {reason} (tapaus #{case})",
"tempmute-on":"{member} on nyt mykistetty, ajaksi {duration} (syy : {reason} | tapaus #{case})",
"d-autounmute":"automaattinen mykistyksen poisto",
"d-unmute":"mykistäjä {}",
"d-invite":"Automaattinen valvoja (Discord kutsu linkki)",
"d-young":"Automaattinen valvoja (liian uusi käyttäjä)",
"d-gived_roles":"Automaattinen tapahtuma (configuraatio annettiin_roolit)",
"d-memberchan":"Automaattinen tapahtuma (configuraatio käyttäjänlaskelma)"}

mc={"contact-mail":"Jos huomaat virheen annetuissa tiedoissa, ota minuun yhteyttä personaalisesti, tai ota yhteyttä tänne: [sivustolla](https://fr-minecraft.net).",
        "serv-title":"Palvelin tiedot {}",
        "serv-0":"Numero pelaajista",
        "serv-1":"Lista 20 ensimmäisestä pealaajasta yhdistettynä",
        "serv-2":"Lista paikalla olevista pelaajista",
        "serv-3":"Latency",
        "serv-error":"Ups, tuntematon virhe havaittu. Yritä uudelleen myöhemmin :confused:",
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
        "role-high":"Oops, this role is too high for me to change. Please move my role above the role `{}` before trying again :confused:",
        'role-color':'The role {} has changed color!'
        }

morpion={'user-begin':'{}, aloita sinä!',
        'bot-begin':"Mennään, minä aloitan!",
        'tip':"\n*Näin peli toimii, kirjoita numero yhden (1) ja yhdeksän (9) välistä, vastaavana valitsevaan tapaukseen. Minä pelaan punaista, sinä sinistä!*",
        'nul':"Tasapeli, kukaan ei voittanut...",
        'too-late':"Sinulla kesti liian kauan valita. Peli pelattu!",
        'pion-1':"Siinä on jo pelinappula!",
        'pion-2':'Pätemätön syöte tapaus',
        'win-1':"Hyvin tehty, {} voitti!",
        'win-2':"Minä voitin! Peli päättyi!",
        'already-playing':"Sinulla on jo peli menossa!"}

perms={"perms-0":"Jäsen/rooli {} ei löytynyt",
        "perms-1":"**'{}' käyttöoikeudet:**\n\n"
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
        "web-default-flow":"{logo}  | New post on {author} ({date}) :\n        {title}\n\n{link}\n\n{mentions}",
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
        "change-10":"This xp system doesn't exist. Here is the list of available systems: {}",
        "change-role": "The '{}' option has been modified with the following roles: {}",
        "change-bool": "The '{}' option has been modified with the value *{}*",
        "change-textchan": "The '{}' option has been modified with the channels {}",
        "change-text": "The option '{}' has been replaced by the following text: \n```\n{}\n```",
        "change-prefix":"The prefix has been successfully replaced by `{}`",
        "change-lang": "The bot language is now in `{}`",
        "change-raid":"The anti-raid security level is now set to **{}** ({})",
        "change-emojis":"The emotions for the option '{}' are now {}",
        "change-xp":"The xp system used is now {}",
        "new_server": "Your server has just been registered for the first time in our database. Congratulations :tada:",
        "see-0":"Enter `!config help` for more details",
        "see-1":"{} server configuration",
        "change-prefix-1":"This prefix is too long to be used!",
        "wrong-prefix":"Oops, it seems this prefix is invalid :thinking: If the problem persists, please choose another one",
        "opt_title":"Option '{}' of server {}",
        "not-found":"The server {} has not yet been registered in the database",
        "need-admin":"You need Administrator permission to execute this command."
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
        "muted_role":"Used role to mute members : {}",
        "noxp_channels":"Channels where you can't get xp: {}",
        "xp_type":"XP system used: {}"}

stats_infos={"not-found":"Kyvytöntä löytää {N}",
        "member-0":"Lempinimi",
        "member-1":"Luotu",
        "member-2":"Liittynyt",
        "member-3":"Saapumis asento",
        "member-4":"Tila",
        "member-5":"Toiminta",
        "member-6":"Järjestyksenvalvoja",
        "member-7":"Infractions",
        "role-0":"Tunniste",
        "role-1":"Väri",
        "role-2":"Voi mainita",
        "role-3":"Jäsen numero",
        "role-4":"Näkyy erikseen muista jäsenistä",
        "role-5":"Arvojärjestyksen asento",
         "role-6":"Ainutlaatuinen jäsen tällä roolilla",
        "user-0":"Tällä palvelimella?",
        "emoji-0":"Animoitu",
        "emoji-1":"Twitchin hallinnossa",
        "emoji-2":"Jänne (boteille)",
        "emoji-3":"Palvelin joka omistaa sen",
        "textchan-0":"Kategoria",
        "textchan-1":"Kuvaus",
        "textchan-2":"NSFW",
        "textchan-3":"Numero verkkokoukuista",
        "textchan-4":":warning: Käyttöoikeuksia puuttuu !",
        "textchan-5":"Kanava",
        "voicechan-0":"Ääni kanava",
        "guild-0":"Palvelin",
        "guild-1":"Omistaja",
        "guild-2":"Maa alue",
        "guild-3":"Teksti : {} | Ääni : {} ({} kategoriat)",
        "guild-4":"Paikalla jäsenet",
        "guild-5":"Numero emojeista",
        "guild-6":"Numero kanavista",
        "guild-7":"{} mukaan lukien {} botit ({} yhdistetty)",
        "guild-8":"Kaksivaiheinen todennus",
        "guild-9":"Turvallisuus taso",
        "guild-10":"Aika ennen kun oli AFK",
        "guild-11.1":"20 ensimmäistä roolia (yhteismäärä {})",
        "guild-11.2":"Lista RooleistaRoles list (yhteismäärä {})",
        "guild-12":"Numero kutsuista",
        "inv-0":"URL linkki",
        "inv-1":"Kutsuja",
        "inv-2":"Käyttöjä",
        "inv-3":"Aikaa jäljellä",
        "inv-4":"Kutsu",
        "inv-5":"Jos tietoa näyttää puuttuvan, valitettavasti se on koska Discord ei kommunikoi sitä",
        "categ-0":"Kategoria",
        "categ-1":"Asento",
        "categ-2":"Teksti : {} | Ääni : {}",
         }

users = {'invalid-card':'Tämä tyyli on pätemätön. Tässä on lista tyyleistä sinä voit käyttää: {}',
        'list-cards':"Here is the list of available rank cards for you: {}",
        'missing-attach-files':'Oops, I\'m missing the permission to Attach Files :confused:',
        'changed-0':'Your xp card now uses the style {}',
        'changed-1':'Oops, an internal error occurred during the processing of the request. Try again later or contact support.',
        'card-desc':"Here is an example of your xp card. You can enter the command `profile card <style>` to change the style\n*Your xp card will only refresh when you have won xp*"}

xp = {'card-level':'TASO',
        'card-rank':'SIJA',
        '1-no-xp':"Sinulla ei ole XP:tä vielä!",
        '2-no-xp':"Tällä jäsenellä ei ole XP:tä!",
        "del-user":"<poistettu käyttäjä>",
        "low-page":"En voi näyttää negatiivista sivu numeroa!",
        "high-page":"Ei ole noin monta sivua!",
        "top-title-1":"Maailmanlaajuinen sijoitus",
        "top-title-2":"Palvelin sijoitus",
        "top-name":"__Top {}-{} (sivu {}/{}):__",
        "default_levelup":["Hey, {user} has just reached **level {level}**! Keep this way!",
        "Crossing to level {level}{user}. Attack and defense increased by 1."
        "Thanks to this level {level}, you can finally use the legendary {random} user {user}",
        "Speech level {level}, {user}. Be careful not to scream too loudly.",
        "{user} is flying to the Top 1 with his level {level}!",
        "But, wouldn't it be a new level for {user}? Level {level}!",
        "Summoner {user} at level {level}. New champions to be won.",
        "{user} evolves to **{user} level {level}!**",
        "Thanks to your level {level}, you have a new point of competence {user}."
        "You have gained {level} levels of experience {user}. Don't forget to use them before they're blown up by a creeper!"
        "I wonder where I'm going to store the {level} of {user}. I'm going to end up with no more room for that many numbers...",
        "Maybe you can finally get your souls back with your level {level}, {user}?",
        "Don't forget to use the money earned from this level {level} to improve the ship, Captain {user}."
        "You are now level {level}, but justice does not yet rule the city, {user}...",
        "By dint of dying, you've gone beyond level {level}, {user}. Now, do that dungeon again and lower that boss."
        "You may be a level {level}{user}, but you'll still get eaten by a deer. Anyway, no one will regret you.",
        "Hey! Wake up {user}! You've gone up to level {level}! Hey!",
        "{user} is level {level}, from eating mushrooms."
        "You may be level {level}, but your princess is still in another castle. ",
        "The force is more powerful in you {user}, now that you are level {level}.",
        "By dodging these millions of infernal bullets, {user} has passed level {level}.",
        "The virus resistance of {user} has increased to {level}. Try not to be eaten by a zombie anyway.",
        "The assassin's discretion {user} has evolved to the level {level}. The brotherhood is counting on you.",
        "Congratulations {user}, you are {level}. Remember to use {random} to keep improving.",
        "Thanks to the level {level}, you can try to win {random} at the raffle, {user} !",
        "Despite your level, it is dangerous to travel alone {user}! Take {random} !",
        "Level {level} for {user}! {random} is available from the seller!",
        "Bravo {user}! You are now level {level}! However, it is still necessary to climb to obtain {random} legendary rarity...",
        "Houston, we have a problem. {user} has passed level {level}!!!!!",
        "You see, the world is divided into two categories: those who levelup and those who don't levelup. You {user}, you levelup to level {level}!!!!",
        "*May the level {level} be with you, {user}.*",
        ],
        "levelup-items":["this sword","this bow","this guitar","this dagger","this hammer","this banana","this portal gun","this mushroom","this shovel", "this shotgun","this magic wand"," this craft table"," this cow", "this window", "this wallpaper", "this emoji", "this bubble gun", "this wrench", "this hood", "this cap", "this bicorne", "this trident", "this lasso", "this purse", "this pin", "this bottle", "this tap", "this toilet","this bike", "this pizza", "this anvil", "this clothespin", "this spoon", "this cape", "this potion", "this pen", "this cushion", "this tractor", "this tea", "this balloon", "this sofa", "this caddy", "this barbecue", "this lightsaber","this pyjama", "this cookie", "this very", "this dragon", "these marshmallows", "these croquettes", "this grappling hook", "this yo-yo", "this demon", "this mechanical arm", "this hot chocolate", "these chips", "this French baguette", "this cheese", "this backpack", "this rock"],
        "top-your":"Sinun sija",
        'rr_list':"Rooli palkinto lista",
        'rr-added':"Rooli `{}` on lisätty oikein tasolle {} !",
        'already-1-rr':"Tälle tasolle on jo rooli konfiguroitu!",
        'no-rr':"Ei roolia konfiguroitu tälle tasolle",
        'rr-removed':"Ei roolia anneta tasolle {} enään",
        'too-many-rr':"You already have {} roles rewards, you can't add more!",
        'rr-reload':"{} updated roles / {} scanned members",
        'no-mee6':"Oops, you have configured the xp system to use the MEE6 system, but this bot is not in the server! Change the system type (`{}config change xp_type` followed by the system name), or invite MEE6 here."
        }