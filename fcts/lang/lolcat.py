#!/usr/bin/env python
#coding=utf-8

current_lang = {'current':'lolcat pliz'}

activity={"rien":"nothin",
"play":"playin",
"stream":"streamin",
"listen":"listenin",
"watch":"watchin"}

admin={
    "change_game-0":"Slect *play*, *watch*, *listen* or *stream* followd by teh naym",
    "msg_2-0":"Operashun in progres '-'",
    "msg_2-1":"No affected memberz",
    "msg_2-2":"wan affected memberé",
    "msg_2-3":"affectd mEmber",
    "bug-0":"Bug #{} not findz",
    "emergency":"A emergency situation have just been declared 4 the boat. Those may bee the case when somebody tries to take controll of my code.\n\
To limit the damagz, I was 4ced to leave all teh servrs I was on imediately, hoping itZ wasn't toooo late.\n\
For much infoZ on de current state ov dis crisis, gonna to my offishial srver: https://discord.me/z_bot (check teh link for the documentashun if it no longer workz: https://zbot.rtfd.io)"
    }

aide={"no-subcmd":"Teh kommand `{0.name}` had not sub~~scribe~~commanD",
"mods":['Moderashun:','Oderz:'],
"footer":"Type {}help cmd 4 mure info abawt an commandZ",
"no-desc-cog":"No more discripton for dis cogg.",
"no-desc-cmd":"No descripshun for those c:o2:mmand",
"cmd-not-found":"Dere are no comand naymme \"{}\"",
"subcmd-not-found":"Thiz commnd have no sUbcommant newmed \"{}\""}

bvn={"aide":"""__**Wilcom 2 teh join end leef mesg modul**__

Dis modul is usd 2 configur a' automatic mesage each tiem membr enters or exits ur servr.

__** ConfiGrationZ**__

`1-` To configur teh channel wer thees mesagez 're writtn, entr `!config change welcome_channel` followd by teh channl ID (rite clik -> "Copy ID" 4 computer, or keep pressin on teh channel -> "Copy ID" 4 phone, but you w'll nede to have enabld teh developer mode to get dis optn).
`2-` To configure a msg, entr `!config change <welcome|leave> <message>`. 4 dis mesage u can uz somm variabl':
 - `{user}` mentionz teh member
 - `{server}` displayz the servr nayme
 - `{owner}` displayz teh servr ownr nam
 - `{member_count}` showz the curent nbr oof memberz
"""}

cases={"no-user":"Unable to find dis usr :eyes:",
    "not-found":"Dis caze was not fund :upside_down:",
    "reason-edited":"Teh ryson for case #{} has been changd!",
    "deleted":"The caze #{} has byn deletd!",
    "cases-0":"{} cases fund: ({}-{})",
    "search-0":"**Uzr:** {U}\n**Type:** {T}\n**Mod:** {M}\n**Date:** {D}\n**Reazon:** *{R}*",
    "search-1":"**Uzr:** {U}\n**Servr:** {G}\n**Type:** {T}\n**Modz:** {M}\n**Date:** {D}\n**Reazon:** *{R}*",
    'title-search':'Case #{}',
    'no_database':"Dude we'v got an databaz outage, so dis command haz been dizabled"}

errors={"cooldown":"Yu are on cold-own for dis comandZ :confused: Plize wait {} moRe secs...",
"badarguments":"W0ops, unabled 2 convrt teh `{c[3]}` parameterz to \"{c[1]}\" tipe :confused:",
"missingargument":"Oops, te argumnt \"{}\" are missin {}",
"membernotfound":"Unabl to found the membr `{}` :confused:",
"usernotfound":"Unabled 2 find teh userZ `{}` :confused:",
"disabled":"Da {} cmd is dizabled :confused:"}

find={"user-0":"naym: {}\nID: {}",
"user-1":"Naym: {}\nID: {}\nServers: {}\nSpeak: {}",
"user-2":"Usr not findz",
"guild-0":"S3rvr not findz",
"guild-1":"Name: {}\nID: {}\nOwnr: {} ({})\nMmbr: {} ({} robots)\nSpeak {}",
"chan-0":"chAnnel not foundz",
"chan-1":"Nayme : {}\nID: {}\nServr: {} ({})",
"help":"Dis commnd allowz 2 find a servr or a chnnel among all the servers on which'z teh bot. U can so seerch 4 a Discord usr's info, no mater if he sharez servr wif me!\
Teh syntax'z `!find <user|channel|guild> <ID>`"}

fun={"count-0":"Countng in progrez...",
    "count-1":"On teh last {} posts, U has postd {} msgs ({}%)",
    "count-2":"You wanna blow up Discord! {e} For obvious performance reasons, I'm gonna impose limit ov {l} msgz.",
    "count-3":"Oops, Im unable to reed dis channel ystory. Pls check mah perms...",
    "fun-list":"Her iz the list ov available fun commandz:",
    "no-fun":"Fun comands haz beeen disabld on dis server. 2 C their list, look at https://zbot.rtfd.io/en/v3/fun.html",
	"osekour":["Oh hum wait, Im finshin watchin mi movi.","We r comin! But wy donot yu answr anymor? Do'nt fak ded dude!","Yeh, we now ther'z an fire, we don'b ned 2 come: we're avin a barbeQ at teh fire stashun.","*Reskue iz curentlly unaivalab, pliz wait untile the and of teh braek*","*Dis numbr doz not exyzt. Pleash try agan with anoder number.*","*Manetenanec ov teh current lien, Srsly . plz twee agaen in 430 hourz.*","*ur mobiel plan has expired. u can buy wan 4 86,25€*","2 moar volumes ov Lord ov teh Rings 2 finish readin, an meh all urz!","Tank u 4 not disturbin us durin teh holidais","Shurry, ther is moar dan tree snowflakz: wuz stuck in teh garaeg","Well haz 2 wait til teh end ov r striek.. R u sayin you dun't knoe?! iz been 2 monfz sinec we startd pliz!"],
    "react-0":"Unable 2 find teh correspondin mssage. U must giv teh mesage ID in da furst argumnt, an teh emoji in da secondz :upside_down:\n Also check dat I haz permishun 2 reed msgs hystory!",
    "thanos":["{0} wus spard by Thanos","Tahnos decidd 2 reduce {0} to ashes. 4 the gud ov humanity...."],
    "piece-0":["Tails!","Heads!"],
    "piece-1":"Faild, 't fell on teh edge!",
    "calc-0":"Nope, result takz too looooooong to load :rofl:",
    "calc-1":"Teh solushuns of the calculation `{}` are `{}`",
    "calc-2":"The solutions of teh calculz `{c}` R `{l[0]}` and `{l[1]}`",
    "calc-3":"The solushun to the calculation `{}` 'z `{}`",
    "calc-4":"Teh calculation `{}` haz nope solushun",
    "calc-5":"Oooops, an error appeared :upside_down: \n `{}`",
    "no-reaction":"Unable 2 add reactions. Plz check mah perms...",
    "cant-react":"I doan haz enough perms 2 send reactions!",
    "vote-0":"U can't put moar than 20 choicez, an' even lesss negativ numbr of choicesz!",
    "blame-0":"Lizt ov availabl namz 4 **{}**",
    "no-database":"As our data ar offline, access to funz commandz iz restricted to guys with permishun \"Manage Server\"",
    "no-embed-perm":"I dont haz permishun 2 \"Embed links\" :confused:",
    "embed-error":"A' error went wrong: `{}`"
    }

infos={"text-0":"""Ho hi hello! I'm {0} !

Im a boat that alow you 2 do a loooooot of tings: modration, mini-gamz, a' xp systèm, stATIstics & many oder super mega *wow* usefull commandz (and totlly pointlesz wanes)! 
U can strt by tipyng `!help` in dis tchat to se the llst for availabl kommands, then `!config see` wil LEtz you see teh configurashun optionz (a website ar in prePARtion)? 

Of helpin me in the creetion of the boat, my ownr an I wouLd like to tahnk Awhikax 4 hiz suport durin the variouz cryzes, Aragorn1202 of al her idees and sentencez full for goob sence, Adri526 fr all dese beautifool loGoz, èmojiz nd profil picts, and Pilotnick54 to review an corec mi Anglish!

:globe_with_meridians: Sum linqs can bee usefull: 
:arrow_forward: Me Discord servr plz : http://discord.gg/N55zY88
:arrow_forward: link to iNVite me to anothr servr : <https://bot.discord.io/zbot>
:arrow_forward: The :b:ot documentashun : <https://zbot.rtfd.io/>
:arrow_forward: My creator's Blue Bird 'ccount : <https://twitter.com/z_runnerr>

Has a nice dayz !""",
"docs":"Her'z teh link 2 the bot doc:",
"stats-title":"**Boat statz**",
"stats":"""**Baut vershun:** {} \n**Nbr ov serverz:** {} \n**Nbr ov visible memberz:** {} ({} **robots**)\n**Nbr ov code lin:** {}\nUzd languages: {}\n**Python vershun :** {} \n**Vershun ov teh `discord.py` lyb:** {} \n**Loadin on teh RAM:** {} GB \n**Loadin on the CPU:** {} % \n**API latency timz:** {} ms""",
"admins-list":"My super-cool admins are : {}"}

infos_2={"membercount-0":"Total nmber of membrz",
"membercount-1":"Numbr ov botz",
"membercount-2":"Numbrz for good people",
"membercount-3":"Nmbr ov god online peepl"}

keywords={"depuis":"sinze",
          "nom":"nayme",
          "online":"on-line",
          "idle":"idle",
          "dnd":"donot disturb me",
          "offline":"oofline",
          "oui":"yup",
          "non":"nop",
          "none":"none",
          "low":"low",
          "medium":"meadium",
          "high":"high",
          "extreme":"Xtrem",
          "aucune":"none",
          "membres":"memberz",
          "subcmds":"subcommands",
          "ghost":"Goast"
          }

kill={"list":["Hi ho ! Oh u, u gonna die!",
          "***BOUM !*** {1} fel unto a trapp posd by {0} !",
          "Luckly, teh grond had cushioned teh fall ov {1} !",
          "{0} shooted \"Fus Roh Dah\" whale {1} was next 2 a cliffff...",
          "NoPE, u cant' stwop bullts with ur h:a:ndz {1} :shrug:",
          "Yu habe to bee __IN__ the elevatorZ {1}, nowt __ab:o2:ve__!!!",
          "{1} stayd 2 cloes 2 teh speakerz durin heavy metal consert.",
          "Stayin withn 10 meterz ov a' atomical exploshun wazn't god idea {1}...",
          "No ! Dooble jumps is nowt posibl {1} !",
          "{1} imitatd Icare... splaaash.",
          "It's nice to had portal gun {1}, but donot opne prtls abOve spadez...",
          "{1} ded. Pice to him sowl... :sneezing_face:",
          "{0} killd {1}",
          "{1} waz shut by {0}",
          "Byyyyyyyyyyyyyyyyyyye {1} ! :ghost:",
          "{1} sew an fluwing anvil fal... on him hed :head_bandage:",
          "{1} comit suiside aftr {0} had cutt hiz connecshun",
          "CawtionZ {1} ! Fire burnZ... alot :fire:",
          "{1} fight zombiZ witout sh:o2:vel",
          "{1} trid 2 hug a crEEperZ",
          "{1}, luva baths r hott, but lava burnZ...",
          "{1} trid 2 do a rcket jump",
          "You shuldn't lissen 2 teh prety melodi ov teh Lullaby, {1} :musical_note:",
          "{2}.exe *has stopeD wurkin*"
          ]}

logs={"slowmode-enabled":"Slwmod enable in {channel} ({seconds}s)",
"slowmode-disabled":"Shlowmode disabld in {channel}",
"clear":"{number} dletd mesage for {channel}",
"kick":"{member} had been kik (reson: {reason} | caze #{case})",
"ban":"{member} have bin :b:an (reashun: {reason} | caseZ #{case})",
"unban":"{member} iz no mor band (rson: {reason})",
"mute-on":"{member} Is know mwuted (reason : {reason} | kase #{case})",
"mute-off":"{member} is not more mutd",
"softban":"{member} had beeen 'softBAnnnnned' (reasun: {reason} | caz #{case})",
"warn":"{member} had been warner: {reason} (case #{case})"}

mc={"contact-mail":"If U notis an errrror in da info providd, plz contact my personale, or report teh errer directlly [with the nice website](https://fr-minecraft.net).",
    "serv-title":"Servr info {}",
    "serv-0":"Numbr of playerz",
    "serv-1":"List ov teh first tweny connected plyerz",
    "serv-2":"List of nice online people",
    "serv-3":"LaTENcy",
    "serv-error":"Oops, an Unown errR occurrd. Plz try again latr :smirk_cat:",
    "no-api":"Error: Unable 2 connect to API pliz",
    "no-ping":"Error: Una:b:le 2 ping dis servr",
    "success-add":"A nize messag wif servr details {} has bin addd to teh channel {} !",
    "cant-embed":"Cannot send embd. Plz make shure the \"Embed linkz\" perm is enabld.",
    "names":("Blok","Entity","Aitem","Comand","Advanshument"),
    "entity-help":"Dis cmd allows U to obtain info 'bout any Minekrahft entity. U can giv itz full or partial naym, in French or English, or even itz identifir. Just enter `!mc entity <name>`",
    "block-help":"This comand allows U to obt:a:in inforation on any Mine-craft bloc pleez. U can give itz full or partial name, in French r English, or evn itz identifier. Just enter `!mc block <name>`",
    "item-help":"Dis command allowz you to earn info 'bout any Minecraft itam. You can gave its full or partial nayme, in French r English, r even its identifier. Just entr `!mc item <name>`",
    "cmd-help":"This comand a-laws yu to obtayn informtionz abut any Mynekrahft commandZ. Al u had 2 doo iz type `!mc entity <nom>`",
    "adv-help":"Dis cmd provids informashunz 'bout any advanshement ov the gayme Minekraft. Simple entr the naime or teh identifer of thE advancemenZ.",
    "no-entity":"Unable 2 find this entity",
    "no-block":"Unable 2 found dis block",
    "no-item":"Unablz to find dis item",
    "no-cmd":"Unable 2 findz dis comand",
    "no-adv":"Unabled to found thiz advunshement",
    "mojang_desc":{'minecraft.net':'Offishul Block Site',
      'session.minecraft.net':'Many-People-Together sessions (obsolete)',
      'account.mojang.com':"Mojang 'ccount managmnt site",
      'authserver.mojang.com': "Authentication servr",
      'sessionserver.mojang.com':'Many-People-Together sessions',
      'api.mojang.com': "API service givn bay Mojang",
      'textures.minecraft.net':'Texture servr (nice skin & capz)',
      'mojang.com':'Official Ex Website'},
    "dimensions":"Width: {d[0]}\nLenght: {d[1]}\nHeight: {d[2]}",
    "item-fields":('ID',"Size ov stack",'Creativ mod tab','Damge points',"Durability points","Toolz able 2 destroy it","Mobs able to drop dis item","Added in da vershun"),
    "entity-fields":('Oh ID','Type','HeartH Points','Atack Pts','Experince Points Releas to Dead','Preferred Biomes',':A:ded in teh version'),
    "block-fields":("ID","Stack size","Creative mod tab","Damage points","Durability","Tool able to destroy it","Mobs able to loot it","Added in the version"),
    "cmd-fields":("Nayme","Sntax","Exmple","Adedd in teh vershuon"),
    "adv-fields":("Named","IDz","Tipe","Actshun","Parent","Childrn","Added on the vershun"),
      }

modo={"slowmode-0":"Teh very-cold-mode is now disabld in this nize place.",
    "slowmode-1":"Impossible to set a frequency higher than two minutes",
    "slowmode-2":"The {} channl iz naw in very-cold-mode. Wait {} secondz be4 sending a mesage.",
    "slowmode-3":"Nope, dis valu iz invalid",
    "cant-slowmode":"Ooops, I dont haz permishun 2 `Manage dis channel` :rolling_eyes:",
    "clear-0":"{} messagz deletd!",
    "need-manage-messages":"Permishun \"Manage Messages\" missing :confused:",
    "need-read-history":"Oooops, I'm missing the perm 2 \"Read Message History\" :confused: ",
    "clear-1":"Ai cann:o2:t delte so few mesages plize",
    "cant-kick":"Perm 'Kick memberz' needed :confused:",
    "kick":"Membr {} haz been kick from dis servr. Just 'cause **{}**",
    "staff-kick":"Yolo NOPE ! U can't kick a-other nice staff mmber!",
    "kick-noreason":"U have just been kicked from the servr {} :confused:",
    "kick-reason":"U haz just been KICZed from the servr {} :confused:\nReason : {}",
    "kick-1":"Seemz that this membr iz tooooo high 4 me to kick him out :thinking:",
    "error":"Oooooops, unknown error :scream: Just waiiiit, 'r contact sport",
    "warn-mp":"U haz receivd 'warnung from *{}* servr: \n{}",
    "staff-warn":"Hey NOPE ! U cant warn 'nother staff nice member!",
    "warn-1":"Nice, membr `{}` haz beeen warnd 4 reezon `{}`",
    "warn-bot":"Nope, cant warn anoder cool boat ^^",
    "warn-but-db":"Our dataz being offline, so ze warning couldnt be savd. Don't worry, this guy did receive his warning in DM :innocent:",
    "staff-mute":"U cant prevent another cool staff member frm speek'ng ",
    "mute-1":"Teh mmber {} haz been silencd for the reezon `{}`!",
    "no-mute":"Oooops, seemz dat teh nice `muted` role doznt exist :rofl: Creat'it nd assign perms yourself",
    "cant-mute":"Ooops, 't seemz dat I dont haz enough perms for that.... Plz give me perm `Manage roles` :eyes:",
    "mute-high":"Ooops, 't sEEms dat `muted` rol iz tooo high 4 me to give it... Plz fiX dis problem by plac'ng my role higher than this nice `muted` role.",
    "already-mute":"Dis membr iz 'lready mute!",
    "already-unmute":"This mber iznt muted!",
    "unmute-1":"Teh mmber {} canow speek 'gain",
    "cant-ban":"Perm 'Ban members' needd :confused:",
    "staff-ban":"NOPE, U can't ban another cool staff guy!",
    "ban-noreason":"U haz just been bannd fr0m the servr {} :confused:",
    "ban-reason":"You haz just been bannd from teh server {} :confused:\nReason : {}",
    "ban":"Mber {} has been banned fr0m dis cool servr. Just 'cause this : **{}**",
    "ban-1":"Maaaw... 'seems dat dis member iz too high 4 me to ban him :thinking:",
    "ban-list-title":"List of bannd membrs ov this nice place '{}'",
    "no-bans":"No mmber seems to be bannd from here",
    "unban":"Mmber {} iz no langer bannd fr0m this servr",
    "cant-find-user":"Ooops, no way 2 find dis usr **{}**",
    "ban-user-here":"Dis nice guy iz not part of teh bannd members list :upside_down:",
    "caps-lock":"Heyz {}, beware of too big letters!",
    "wrong-guild":"Oooops, it seemz dis emoji dont belang dis server <:owo:499661437589913621>",
    "cant-emoji":"Oooops, I'm missng teh perm `Manage emojis` <:owo:499661437589913621>",
    "emoji-valid":"Teh emojy {} haz been modified 2 allow only teh roles `{}`",
    "emoji-renamed":"Teh emotz {} had bin renaamd!",
    "cant-pin":"Wups, I do'nt had permit to pin teh messag",
    "pin-error":"Oops, I ca't found dat msage (Error~~404~~ : `{}`)",
    "pin-error-3":"WoOops, **im**possibl 2 pin dis mesge (doo u hav mor' tahn fYfti pinnd mesages?). Error : `{}`"
    }

perms={"perms-0":"Membr/role {} not findz",
        "perms-1":"**'{}' permissung:**\n\n"
       }

rss={"yt-help":"To seerch for a youtwube channel, you may enter the channil ID. You will found it at teh and of the strin url, it can be 8ther the nayme, or a strin of randem characteRs. \
*Tip: some channels are already fellid in me code. Sometimez you can just put `neil3000` or `Oxisius`* :wink:",
"tw-help":"To seerch 4 a twittr acount, you must entr the identifierz of this accounT. You would find it at the end from the strin url plz, it usualy corrresponds to the uer'z naym. \
For ex:a:mple, for %https://twitter.com/Mc_AsiliS*, u must entr `Mc_AsiliS`.",
"web-help":"To search for an rss fead from any wibsite, simplyy enter the rss/atom feedz url ass a para-meter. If teh feed is walid, I wil sent you the las' article publishd on dis site. \
*Tip: s:o2:me rss feeds are allready flled in my code. Sometimes u can just put `fr-minecraft` or `minecraft.net`* :wink:",
"web-invalid":"Oops, dis url addresssss is INValid :confused:",
"nothing":"I finnd nothin on this searrch :confused:",
"success-add":"Teh rss feed for type '{}' with lik <{}> have bein prperly addded in the cannel {} !",
"invalid-link":"Oops, dis url ADress is unvalid or outcompletz :confused:",
"fail-add":"An fAtal erroR have occurred whale proczzing ur respond. Plz trye again laterz, r contakt boat suPPORt (entr teh comand `botinfo` 4 srver link)",
"flow-limit":"Fr pirformunce reesons, U can notz track mor than {} rss feeds per srver.",
"yt-form-last":"""{logo}  | Her the lazt vid from {author}:
{title}
Publishd on {date}
Link : {url}
""",
"tw-form-last":"""{logo}  |  Hre is teh last twit of {author}:
Written on {date}

{title}

Zelda : {url}
""",
"web-form-last":"""{logo}  |  Here are the lazt P:o2:stz of {author}:
**{title}**
*Writen by {date}*
UrL : {link}""",
"yt-default-flow":"{logo}  | Naw videogramm of {author} : **{title}**\nPublishd on {date}\nLink : {link}\n{mentions}",
"tw-default-flow":"{logo}  | New tweat for {author} ! ({date})\n\n{title}\n\nLink : {link}\n\n{mentions}",
"web-default-flow":"{logo}  | New postz on {author} ({date}) :\n    {title}\n\n{link}\n\n{mentions}",
"list":"*Tipe teh nbr of the floww 2 modyfi by*\n\n**Zelda - Typez - cHanel - Mentionz**\n",
"list2":"*Type teh nmberZ ov the flowz 2 deletz*\n\n**Lnk - Tipe - Chanell**\n",
'tw':'Twiter',
'yt':'YouTwube',
'web':'Weeb',
'mc':'Minekrraft',
'choose-mentions-1':"Pleese chose the flow 2 modify",
"choose-delete":"Plz chouse teh flo to delet",
"too-long":"You weighted tooooooo lOng, sory :hourglass:",
"no-roles":"No more role hAVe bean configurated yetz.",
"roles-list":"Her iz teh lis for rolez alreedy indicatd: {}",
"choose-roles":"Which roles should bee piing?",
"not-a-role":"The rOle `{}` was not finndz. Try against:",
"roles-0":"Thes feed have been editd 2 mention the roles {}",
"roles-1":"Those feeed has beeen modifiedz to do not ping ani role",
"no-feed":"Oops, u donot hav any rss feds 2 managez plz!",
"delete-success":"Teh flow had bein sussellfuccy delet!",
"no-db":"As the databaz is auffline, dis feature iz temporarly disabled :confused:",
"guild-complete":"{} rss streams haz correctly rechargd in {} seconds!",
"guild-error":"A error occurrd durin teh load: `{}`\nIf you think dis err iz not your auwn, u can report it to support staff"
}

server={"config-help": "Dis cmd is mainly usd 2 configur ur srver. By doin `!config see [option]` u will get \
overview ov teh currnt configuraishun, and supr cool servr masters can enter `!config change <option> role1, role2, role3...` \
to modify configuraishun, or `!config del <option>` 2 reset teh option (`!config change <option>` works same).",
        "change-0": "Dis option doz not exist :confused:",
        "change-1": "Oops, an internal error occurrd...\nBut doan worry, we'r on teh place: http://asset-5.soupcdn.com/asset/3247/3576_5092_600.jpeg",
        "change-2": "The '{}' opshun value haz been deleted",
        "change-3": "Teh role '{}' waz not findz :innocent: (Check upper caze and special characters)",
        "change-4": "Teh '{}' opshun expects a boolean (True/False) parameter in value :innocent:",
        "change-5": "Teh channel '{}' waz not found :confused: (Enter the exact mention, name 'r identifier of teh channel(s)",
        "change-6": "Teh '{}' :o:ption expects a numbr in parameter :innocent:",
        "change-7": "Dis language is not available. Here is the list of currently supported languages: {}",
        "change-8": "Ups, dis lvl doz nope exist. Heer iz da list ov currrently availaible levelz: {}",
        "change-9": "Ups, da emoji `{}` wasnt findz",
        "change-role": "The '{}' option haz been edted with teh following rolz: {}",
        "change-bool": "The '{}' opzion haz been modified wif the value *{}*",
        "change-textchan": "The '{}' opshun has been modifid wif teh channelz {}",
        "change-text": "Teh opshun '{}' haz been replacd by the followin txt: \n```\n{}\n```",
        "change-prefix":":cat: The prefiX has been nicely replaced by `{}`",
        "change-lang": "Teh bot lang is naw in `{}`",
        "change-raid":"Teh anti-rayd security lvl iz naw set 2 **{}** ({})",
        "change-emojis":"Teh emojiz 4 the opshun '{}' are naw {}",
        "new_server": "Ur server haz just been written for da furst time in r database. Congratulashuns :tada:",
        "see-0":"Enter `!config help` 4 more details",
        "see-1":"{} server configurashiun",
        "change-prefix-1":"Dis prèfix:x: iz too long 2 be used!",
        "wrong-prefix":"Oooops, it seemz dis prefix is no valid :thinking: If teh problem persists, plz choose a' other one",
        "opt_title":"Opzion '{}' of srver {}",
        "not-found":"Teh server {} haznt been registered yet in da data board"
    }

server_desc={"clear": "Lizt of rawles dat can us teh 'clear' commend: {}",
             "slowmode": "Llst of rolz that ca' use 'slowmode' and 'freeze' commmandz: {}",
             "mute": "Lis of roles dat kan us the 'mute' commmand: {}",
             "kick": "Lizt of roles taht caan use tee 'kick' commad: {}",
             "ban": "List for r:o2:les that cawn use this command 'ban': {}",
             "warn": "Lizt of rawle thut can emploi commanDz 'warn' end 'cases' pliz: {}",
             "say": "Lizt of Rawles dat can wuse teh comnd 'say' : {}",
             "gived_roles": "Lizt from rles otomaticall giveD 2 knew mmbr: {}",
             "save_roles": "Can role bee save:b: wHen an membr leive, in case him retrns? {}",
             "enable_xp": "Shald teh xperiense systèm be enabld? {}",
             "anti_caps_lock": "Shuld the baot sent a mssge when a mmBEr sents TOO MANY C:a:PITAL LETERZ ??!!??! {}",
             "enable_fun": "R teh c0mmands lysteb in te `!fun` comand enubld? {}",
             "hunter": "Lyst for al cat roums in wich teh gamz *Hunter* are actved: {}",
             "welcome_channel": "Lst of canels whe're to sen wilcume/leivz mesage': {}",
             "bot_news": "Liist for channnnels were 2 sendz bot nweZ: {}",
             "modlogs_channel":"Chanel where 2 sent modrashun wOods: {}",
             "poll_channels": "List oof channl whre :thumbsup: & :thumbsdown: réactonz would be aut:o2:maticall ad to aech msg pliz : {}",
             "welcome": "Missge snt whem a mber arived :: {}",
             "leave": "Mesae sen when an meberz leave: {}",
             "language": "Cuurent zbot languge 4 dis lolcat: **{}**",
             "prefix":"Currnt baot prfx: {}",
             "membercounter":"Channel dis-playin nmberz from memberz in iz nayme: {}",
             "anti_raid":"Lev3l of anti-rayderz protect: {} \n*([Dowcumetaton](https://zbot.rtfd.io/en/latest/moderator.html#anti-raid))*",
             "vote_emojis":"Emojiz use 4 powll reacts: {}",
             "help_in_dm":"Sent help mess:a:ge on Prvte Msage? {}"}

stats_infos={"not-found":"Unable 2 found {}",
            "member-0":"Lttle nayme",
            "member-1":"Born at",
            "member-2":"New from",
            "member-3":"Arrivald pose",
            "member-4":"Statu",
            "member-5":"Actvty",
            "member-6":"Cat MasterZ",
            "role-0":"IDz",
            "role-1":"Colorr",
            "role-2":"Mentionnable",
            "role-3":"Nmber ov members",
            "role-4":"Lonely supeR :a:lon roleZ",
            "role-5":"Hierarchical posishun",
             "role-6":"Lonely userz",
            "user-0":"On dis servr?",
            "emoji-0":"Animate",
            "emoji-1":"Managd by Twiitch",
            "emoji-2":"String (4 roboats)",
            "textchan-0":"Catègoryz",
            "textchan-1":"Descripshun",
            "textchan-2":"Nut 4 kIdz (NSFVV)",
            "textchan-3":"Numbr ov webhooks",
            "textchan-4":":warning: Mizzing permz !",
            "textchan-5":"Chanel",
            "voicechan-0":"Singing ch4nnel",
            "guild-0":"Guild",
            "guild-1":"Auwner",
            "guild-2":"Rejion",
            "guild-3":"Txt : {} | Vcall : {} ({} categoreez)",
            "guild-4":"Green pple",
            "guild-5":"Numbr ov emojiz",
            "guild-6":"Numbr ov cats",
            "guild-7":"{} incluwdin {} nice robots ({} connect)",
            "guild-8":"2F authuntificashun",
            "guild-9":"Secure lvl",
            "guild-10":"Tim be4 being AFK",
            "guild-11.1":"20 first rawles (tot {})",
            "guild-11.2":"Rol list (totAl {})",
            "inv-0":"URL lnk",
            "inv-1":"Inviter",
            "inv-2":"Uzz",
            "inv-3":"Time right be4 explosion",
            "inv-4":"InvitashiunZ",
            "inv-5":"If ifo seems missin, it is sadly cuz Discord didnt send dem",
            "categ-0":"Categori",
            "categ-1":"Posishun",
            "categ-2":"Textz : {} | Vocaal : {}",
             }