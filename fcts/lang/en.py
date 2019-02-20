#!/usr/bin/env python
#coding=utf-8

current_lang = {'current':'en'}

activity={"rien":"nothing",
"play":"playing",
"stream":"streaming",
"listen":"listening to",
"watch":"watching"}

admin={
    "change_game-0":"Select *play*, *watch*, *listen* or *stream* followed by the name",
    "msg_2-0":"Operation in progress...",
    "msg_2-1":"No affected members",
    "msg_2-2":"1 affected member",
    "msg_2-3":"affected members",
    "bug-0":"Bug #{} not found",
    "emergency":"An emergency situation has just been declared for the bot. This may be the case when someone tries to take control of my code.\n\
To limit the damage, I was forced to leave all the servers I was on immediately, hoping it wasn't too late.\n\
For more information on the current state of the crisis, go to my official server: https://discord.me/z_bot (check the link from the documentation if it no longer works: https://zbot.rtfd.io)"
    }

aide={"no-subcmd":"The command `{0.name}` has no subcommand",
"mods":['Moderation:','Other:'],
"footer":"Type {}help command for more info on a command",
"no-desc-cog":"No description for this cog.",
"no-desc-cmd":"No description for this command",
"cmd-not-found":"There is no command nammed \"{}\"",
"subcmd-not-found":"This command has no subcommand named \"{}\""}

bvn={"aide":"""__**Welcome to the join & leave message module**__

This module is used to configure an automatic message each time a member enters or exits your server.

__** Configuration**__

`1-` To configure the chat room where these messages are written, enter `!config change welcome_channel` followed by the channel ID (right click -> "Copy ID" for computer, or keep pressing on the channel -> "Copy ID" for phone, but you will need to have enabled the developer mode to get this option).
`2-` To configure a message, enter `!config change <welcome|leave> <message>`. For this message you can use some variables:
 - `{user}` mentions the member
 - `{server}` displays the server name
 - `{owner}` displays the server owner name
 - `{member_count}` shows the current number of members
"""}

cases={"no-user":"Unable to find this user :eyes:",
    "not-found":"This case was not found :confused:",
    "reason-edited":"The reason for case #{} has been changed!",
    "deleted":"The case #{} has been deleted!",
    "cases-0":"{} cases found: ({}-{})",
    "search-0":"**User:** {U}\n**Type:** {T}\n**Moderator:** {M}\n**Date:** {D}\n**Reason:** *{R}*",
    "search-1":"**User:** {U}\n**Guild:** {G}\n**Type:** {T}\n**Moderator:** {M}\n**Date:** {D}\n**Reason:** *{R}*",
    'title-search':'Case #{}',
    'no_database':"Due to a temporary database outage, this command has been disabled"}

errors={"cooldown":"You are on cooldown for this command :confused: Please wait {} more seconds...",
"badarguments":"Oops, unable to convert the `{c[3]}` parameter to \"{c[1]}\" type :confused:",
"missingargument":"Oops, the argument \"{}\" is missing {}",
"membernotfound":"Unable to find the member `{}` :confused:",
"usernotfound":"Unable to find the user `{}` :confused:",
"disabled":"The command {} is disabled :confused:",
"duration":"The duration `{}` is invalid"}

find={"user-0":"name: {}\nID: {}",
"user-1":"Name: {}\nID: {}\nServers: {}\nOwner of: {}\nLanguages: {}",
"user-2":"User not found",
"guild-0":"Server not found",
"guild-1":"Name: {}\nID: {}\nOwner: {} ({})\nMembers: {} (including {} bots)\nLanguage: {}",
"chan-0":"Channel not found",
"chan-1":"Name : {}\nID: {}\nServer: {} ({})",
"help":"This command allows to find a server or a salon among all the servers on which is the bot. You can also search for a Discord user's information, no matter if he shares a server with me!\
The syntax is `!find <user|channel|guild> <ID>`"}

fun={"count-0":"Counting in progress...",
    "count-1":"On the last {} posts, you have posted {} messages ({}%)",
    "count-2":"You wanna blow up Discord! {e} For obvious performance reasons, I will impose a limit of {l} messages.",
    "count-3":"Oops, I'm unable to read this channel history. Please check my permissions...",
    "fun-list":"Here is the list of available fun commands:",
    "no-fun":"Fun commands have been disabled on this server. To see their list, look at https://zbot.rtfd.io/en/v3/fun.html",
    "osekour":["Wait, I'm finishing watching my movie.","We're coming! But why don't you answer anymore? Don't fake death!","Yes, we know there's a fire, we don't need to come: we're having a barbecue at the fire station.","*Rescue is currently unavailable, please wait until the end of the break*","*This number does not exist. Please try again with another number.*","*Maintenance of the current line. Please try again in 430 hours.*","*Your mobile plan has expired. You can buy one for 86,25€*","Two more volumes of Lord of the Rings to finish reading, and I'm all yours!","Thank you for not disturbing us during the holidays","Sorry, there are more than 3 snowflakes: we're stuck in the garage","We'll have to wait until the end of our strike... Are you saying you don't know?! It's been two months since we started!"],
    "react-0":"Unable to find the corresponding message. You must enter the message ID in the first argument, and the emoji in the second :upside_down:\n Also check that I have permission to read the message history!",
    "thanos":["{0} was spared by Thanos","Thanos decided to reduce {0} to ashes. For the good of humanity...."],
    "piece-0":["Tails!","Heads!"],
    "piece-1":"Failed, it fell on the edge!",
    "calc-0":"The result takes too long to load:/",
    "calc-1":"The solutions of the calculation `{}` are `{}`",
    "calc-2":"The solutions of the calculation `{c}` are `{l[0]}` and `{l[1]}`",
    "calc-3":"The solution to the calculation `{}` is `{}`",
    "calc-4":"The calculation `{}` has no solution",
    "calc-5":"Oops, an error occured: `{}`",
    "no-reaction":"Unable to add reactions. Please check my permissions...",
    "cant-react":"I don't have enough permissions to send reactions!",
    "no-emoji":"Unable to find this emoji!",
    "vote-0":"You can't put more than 20 choices, and even less a negative number of choices!",
    "blame-0":"List of available names for **{}**",
    "no-database":"As our database is offline, access to fun commands is restricted to people with permission \"Manage Server\"",
    "no-embed-perm":"I don't have permission to \"Embed links\" :confused:",
    "embed-error":"An error has occurred: `{}`"
    }

infos={"text-0":"""Hello! I'm {0} !

I'm a bot that allows you to do a lot of things: moderation, mini-games, an xp system, statistics and many other super useful commands (and totally pointless ones)! 
You can start by typing `!help` in this chat to see the list of available commands, then `!config see` will let you see the configuration options (a website is in preparation). 

For helping me in the creation of the bot, my owner and I would like to thank Awhikax for his support during the various crises, Aragorn1202 for all his ideas and sentences full of good sense, Adri526 for all these beautiful logos, emojis and profile pics, and Pilotnick54 to review and correct my English!

:globe_with_meridians: Some links may be useful: 
:arrow_forward: My Discord server : http://discord.gg/N55zY88
:arrow_forward: A link to invite me to another server : <https://bot.discord.io/zbot>
:arrow_forward: The bot documentation : <https://zbot.rtfd.io/>
:arrow_forward: My creator's Twitter account : <https://twitter.com/z_runnerr>

Have a nice day!""",
"docs":"Here is the link to the bot documentation:",
"stats-title":"**Bot statistics**",
"stats":"""**Bot version:** {} \n**Number of servers:** {} \n**Number of visible members:** {} ({} **bots**)\n**Number of code lines:** {}\n**Used languages:** {}\n**Python version :** {} \n**Version of the `discord.py` lib:** {} \n**Loading on the RAM:** {} GB \n**Loading on the CPU:** {} % \n**API latency time:** {} ms""",
"admins-list":"The administrators of this bot are : {}",
"prefix":"List of currently usable prefixes:"}

infos_2={"membercount-0":"Total number of members",
"membercount-1":"Number of bots",
"membercount-2":"Number of humans",
"membercount-3":"Number of online members"}

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
"warn":"{member} has been warned: {reason} (case #{case})",
"tempmute-on":"{member} is now muted for {duration} (reason : {reason} | case #{case})",}

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
    "ban-list-title":"List of banned members of the server '{}'",
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
    }

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
to modify a configuration, or `!config del <option>` to reset the option (`!config change <option>` works the same way).",
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

server_desc={"clear": "List of roles that can use the 'clear' command: {}",
             "slowmode": "List of roles that can use 'slowmode' and 'freeze' commands: {}",
             "mute": "List of roles that can use the 'mute' command: {}",
             "kick": "List of roles that can use the 'kick' command: {}",
             "ban": "List of roles that can use the command 'ban': {}",
             "warn": "List of roles that can use commands 'warn' and 'cases': {}",
             "say": "List of roles that can use the command 'say' : {}",
             "gived_roles": "List of roles automatically given to new members: {}",
             "save_roles": "Should roles be saved when a member leaves, in case he returns? {}",
             "enable_xp": "Should the xp system be enabled? {}",
             "anti_caps_lock": "Should the bot send a message when a member sends too many capital letters? {}",
             "enable_fun": "Are the commands listed in the `!fun` command enabled? {}",
             "hunter": "List of all chat rooms in which the game *Hunter* is active: {}",
             "welcome_channel": "List of channels where to send welcome/leave messages: {}",
             "bot_news": "List of channels where to send bot news: {}",
             "modlogs_channel":"Channel where to send moderation logs: {}",
             "poll_channels": "List of channels where :thumbsup: and :thumbsdown: reactions will be automatically added to each message : {}",
             "welcome": "Message sent when a member arrives: {}",
             "leave": "Message sent when a member leaves: {}",
             "language": "Current bot language for this server: **{}**",
             "prefix":"Current bot prefix: {}",
             "membercounter":"Channel displaying number of members in its name: {}",
             "anti_raid":"Level of anti-raid protection: {} \n*([Documentation](https://zbot.rtfd.io/en/latest/moderator.html#anti-raid))*",
             "vote_emojis":"Emojis used for poll reactions: {}",
             "help_in_dm":"Send help message in Private Message? {}",
             "muted_role":"Used role to mute members : {}"}

stats_infos={"not-found":"Unable to find {}",
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