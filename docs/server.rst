=======================
⚙ Server configuration
=======================


--------------
Config options
--------------


Recently, ZBot has features that can be modified per server, to make each server unique. You will find the language of the bot, the activation of certain options (such as the xp system), the list of roles authorized to use certain commands (ban, clear...), the welcome messages, and many other options.

The list of options continues to grow as development progresses, that's why a website is planned to make server configuration easier.

.. note:: For the curious, know that all the configuration of each server is entirely saved in a MySQL database file, which makes its use easier than a simple txt or csv file.

.. warning:: Recently, it has become possible to do without the names of the subcommands. Thus :code:`config 2` is equivalent to :code:`config see 2`, and :code:`config xp_rate 1.4` to :code:`config set xp_rate 1.4`.

Watch
-----

**Syntax:** :code:`config see [option | page]`

The `see` subcommand allows you to see the value of a configuration, with a mini explanatory sentence. If no option is specified, the entire configuration will be displayed in a single message. Note that the bot can suffer a slight latency since this data is stored in an external database.

The page number is used because the options are too numerous to be displayed on a single screen. They have therefore been grouped by page of 20, accessible via this number (default 1).

A detailed list of all options is available `below <#list-of-every-option>`__ .

.. warning:: To display this command correctly, ZBot only needs Embed links permission.


**Syntax:** :code:`config list`

This command will give you a list of all the bot configuration options, in case you are looking for a specific name, or if you just want to make sure you know them all. However, no details will be given, to know what these options are used for you will have to go to the documentation.


Modify
------

**Syntax:** :code:`config set <option> <value>`

This subcommand allows you to modify the value of an option. Just enter the exact name of the option and its value. A validation message will then be sent if the request has been correctly executed.

If the value contains several objects, such as a list of roles or channels, they must be separated by commas, like this: :code:`config set clear_allowed_roles Admin, Moderators, Special role for Special people`. Please note that not all configurations support multiple values (for example, it is not possible to have multiple prefixes).

.. note:: When the value takes the form of roles, for more comfort you are not obliged to mention them: the exact name or the identifier of the role is enough. The same goes for chanels.



Delete
------

**Syntax:** :code:`config del <option>`

This subcommand can be useful to reset an option to its default value. By executing this command, the option will be deleted and will take the same value as originally.


List of every option
--------------------

* anti_caps_lock: Boolean indicating whether the bot should send a warning message when a message with too much capitalization is sent. Default is True.
* anti_raid: Anti-raid protection with some useful features. More information `here <moderator.html#anti-raid>`__. Default level: 0
* ban_allowed_roles: List of roles allowed to use the `ban <moderator.html#ban>`__ command. By default, none.
* bot_news: List of channels to which new bot products will be sent. These are the new bugs found as well as the new features added. None by default.
* clear_allowed_roles: List of roles allowed to use the `clear <moderator.html#clear>`__ command. By default, none.
* compress_help: Boolean indicating whether the full help message (without any specified command/module) should show every command or only their count
* delete_welcome_on_quick_leave: Boolean indicating whether the welcome message should be deleted if the member leaves the server quickly. Default is :code:`False`.
* description: Description of the server, used for the `info server <infos.html#info>`__ command and potential partners. Default empty.
* enable_fun: Boolean indicating if the fun part (documentation in preparation) is activated. If so, all commands in this section will be available. Default is :code:`True`.
* enable_xp: Boolean indicating whether the xp system is activated. Default is :code:`True`.
* help_in_dm: Boolean indicating whether the help command message should be sent as a private message or not. If the value is set to :code:`True`, the message will be sent in DM or as an ephemeral message.
* kick_allowed_roles: List of roles allowed to use the `kick <moderator.html#kick>`__ command. By default, none.
* language: Language of the bot. Currently only the languages :code:`fr` (French), :code:`en` (English), :code:`fi` (Finnish) and :code:`de` (German) are available (also you can use :code:`lolcat` or :code:`fr2` for more fun). The change takes place as soon as the order is validated by the system. Default :code:`fr`.
* leave: Message sent when a member leave your server. Some variables are usable, the same as for the welcome message.
* levelup_channel: Channel where the bot will send every levelup announcement message. It can be either a text channel, or "none" for no channel (Axobot won't send any levelup channel), or "any" if you want it in the same channel as the message. Default to any.
* levelup_msg: Message to send when someone reaches a new XP level. You can use :code:`{level}` variable to include the reached level, and :code:`{user}` to mention the user (or `{username}` if you only want the name). Default is a random sentence.
* membercounter: A voice salon whose name displays the number of members on the server
* modlogs_channel: Channel where all moderation logs (ban, warn, clear...) will be sent.
* morpion_emojis: List of emojis used to play on tic-tac-toe. Two emojis must be entered: one for the bot, and one for the player. Discord emojis as well as server emojis can work.
* mute_allowed_roles: List of roles allowed to use the `mute <moderator.html#mute-unmute>`__ command. By default, none.
* muted_role: Role used to mute your members. If no role is specified, Axobot will check for any role called "muted", and create one if needed, with basic permissions.
* noxp_channels: List of text channels where members will not be able to earn any exp. Not necessary if XP is disabled in your server.
* partner_channel: One channel where every partners of the server will be displayed. Default to None.
* partner_color: The color of the partners embeds. Can be hex, integer or common english names. Default to #a713fe.
* partner_role: A role given to every administrator of a partner server. Default to None.
* poll_channels: List of channels in which the bot will add the reactions 👍 and 👎 to each message
* prefix: Character string that will be the bot prefix, for all commands, beginning with the validation message. The prefix must be between 1 and 5 characters long. By default, :code:`!`.
* rank_in_dm: Boolean indicating whether the rank command message should be sent as a private message or not. If the value is set to :code:`True`, the message will be sent in DM or as an ephemeral message.
* say_allowed_roles: List of roles allowed to use the `say` command. By default, none.
* slowmode_allowed_roles: List of roles allowed to use the `slowmode <moderator.html#slowmode>`__ and `freeze <moderator.html#freeze>`__ commands. By default, none.
* ttt_display: How to use the tic-tac-toe game. "Disabled" will prevent your users from playing it, "normal" will use it as usual and "short" will avoid spam messages.
* update_mentions: A list of roles which will be mentioned in each update changelog. You can enable those changelogs with the `bot_news` option. Default to None.
* voice_category: Category used by the automated voice channels system (see `below <server.html#voice-channels-managment>`__)
* voice_channel: Channel used by the automated voice channels system (see `below <server.html#voice-channels-managment>`__)
* voice_channel_format: Name format used by the automated voice channels system (see `below <server.html#voice-channels-managment>`__)
* voice_roles: List of roles given to people being in a voice channel
* vote_emojis: List of emojis that the bot will have to use when there is a voting message. This case may occur when using the vote command, or in a poll channel.
* warn_allowed_roles: List of roles allowed to use the `warn <moderator.html#warn>`__ and `cases <moderator.html#handling-cases>`__ commands. By default, none.
* welcome: Message sent when a member joins your server. Some variables are usable, enter the `welcome <infos.html#welcome>`__ command to see them.
* welcome_channel: List of channels where messages when a member joins/leaves the server will be sent. By default, none.
* welcome_roles: List of roles automatically given to members when they join the server. It is necessary that the bot is above the roles in question, and that it has the permission "Manage roles".
* xp_rate: Exp modifier, which multiplies the gain of xp by this number. It must be between 0.1 and 3, rounded to the nearest 1/100.
* xp_type: Type of XP system to use: :code:`global` if you want to use the accross-server system, common with every other servers which use it, or :code:`local` if you want a more private system. There is also a :code:`mee6-like` system, which uses the same rules as the MEE6 bot, and is also local. Default to :code:`global`.


---------
XP System
---------

The xp system is a system for evaluating a person's activity on a server using a point system. Each message brings a certain number of points to its author, allowing them to gain in level and to rise in the ranking. To avoid having a too easy system, each level is a bit more difficult to reach than the previous one, and security measures have obviously been taken against spam or cheating.


Configure your server
---------------------

There are several ways to customize your xp system. In particular, you have 4 `configuration options <server.html#config-options>`__, each one modifying a characteristic. And more are to come!

- **Enable/disable xp:** it is possible to enable or disable the entire xp system for your server via the option :code:`enable_xp`. If it is set to 'true' the system is enabled, otherwise it will be 'false'. By default 'false'.

- **Change the levelup message:** the bot automatically uses a long list of random messages for your members' level changes, but you can put a single one written by you via the option :code:`levelup_msg`. It is up to you to use then :code:`{user}` to mention the member, :code:`{level}` for his level and :code:`{username}` for his simple name (without notifications).

- **Select the type of xp:** there are natively three different xp systems at Axobot, modifiable with the option :code:`xp_type`: a :code:`global`, in common with all servers using this system (default), a :code:`local` respecting the same calculations but without synchronization between the servers, and a :code:`mee6-like` which uses the same rules as the famous MEE6 bot.

- **Change the gain rate of xp:** if you find that your members are not earning xp fast enough (or too fast), or if you want to make a special event xp for a limited time, you can add a gain modifier between x0.1 and x3, which will multiply by its value each point of xp earned. Not usable for the global xp system, of course. Option name: :code:`xp_rate`.

- **Prevent xp in some channels:** although Axobot prevents people from earning xp with its commands, it cannot detect commands from other bots. So you can prevent your members from earning xp in certain channels via the :code:`noxp_channels` option, which contains a list of all channels where your users can't have any experience points.

- **Select a channel where to send levelup messages:** sometimes levelup messages can be a bit spammy. So you have an option to select a single channel where to send level up messages. It is also possible to disable these messages via the same option. Enter the command :code:`config set levelup_channel` followed by the name of your channel, or an other special value ("none" to disable the message, "any" to select the current channel, or "dm" to send in the user's Direct Messages).



Roles rewards
-------------

Roles rewards are roles given to your members when they reach a certain level of xp. These levels are defined by you (or by anyone with "Manage Server" permission), and you can add up to 7 rewards per server.

The main command to manage these roles is :code:`roles_rewards` (or its alias :code:`rr`). Here is the list of commands currently available :

* :code:`roles_rewards add <level> <role>` : allows you to add a new role to the list of roles-rewards. The level is at least 1, without maximum, and to give the role you can provide either the Identifier or the name.

* :code:`roles_rewards remove <level>` : allows you to delete a role-reward at a certain level, to prevent the next people reaching that level from getting the role. People currently with this role will not lose it, unless you perform a reload via the following command.

* :code:`roles_rewards reload` : reload all roles, to check that each member has the right roles. If a member has excess role-reward, they will be removed; similarly, if a member misses certain roles, they will be assigned to them.

* :code:`roles_rewards list` : lists all currently configured roles-rewards, with their corresponding level, as well as the maximum number of roles allowed for your server. The bot must have "`Embed Links <perms.html#embed-links>`__" permission.

.. warning:: For these roles to work properly, the bot **must** have "`Manage roles <perms.html#manage-roles>`__" permission. The roles to be given or removed **must** also be lower than the role of Axobot in your server hierarchy (Server Settings > Roles tab).


---------------
Partners system
---------------

As a server grows, it is not uncommon to see partnerships formed with other servers. Some may even partner with bots. Axobot therefore offers a system to manage these partnerships in a clean and automatic way. Thanks to this system you can add, edit or remove partners in a few commands, and they will all be displayed in the same place, with the main information about them.

This information on partners is refreshed every 7 hours, starting at 1am (Paris time). It is currently impossible to reload the list yourself, only a Axobot administrator can do so.


Add a partner
-------------

**Syntax:** :code:`partner add <invite> [description]`

Allows you to add a server or bot to your partner list. The invitation must be either a server invitation (starting with discord.gg) or a bot invitation (discord.com/oauth). This invitation will be used to synchronize the partner, so make sure it does not expire.


Change the embed color
----------------------

**Syntax:** :code:`partner color <new color>`

Modifies the color of the partner embed, i. e. the color of the bar to the left of the presentations. An alias exists with the subcommand "colour".


Modify a description
--------------------

**Syntax:** :code:`partner description <ID> <new message>`

Adds or modifies the description of a partner. The identifier must be that of the partnership, obtainable via the command `partners list` or under the embed displayed in the partners' lounge.


Change a server invite
----------------------

**Syntax:** :code:`partner invite <ID> [new invite]`

It often happens that for X reason an invitation becomes invalid. Problem: Axobot uses the partner invitation to synchronize partners with the channel. There is therefore a command to quickly change the invitation of a server.

.. note:: If no new invitation is given in the command, the bot will send you the one currently in use.


List every partners
-------------------

**Syntax:** :code:`partners list`

Lists all the partners that your server currently has. The bot will display the name of the partner, the type (server or bot), and the date of addition. You will even have the list of servers that have added you as a partner!

.. warning:: For a better display of the list, it is recommended to give "`Embed Links <perms.html#embed-links>`__" permission to the bot.


Reload your list
----------------

**Syntax:** :code:`partner reload`

Allows you to remove a partner from the list. You will be asked for a confirmation, to avoid misuse. Once a partner is removed, you must reconfigure it completely if you want to put it back into the channel.


Remove a partner
----------------

**Syntax:** :code:`partner remove <ID>`

Allows you to remove a partner from the list. You will be asked for a confirmation, to avoid misuse. Once a partner is removed, you must reconfigure it completely if you want to put it back into the channel.

-------------
Server backup
-------------

Axobot has a system to backup your server, saving your roles, channels, emojis, webhooks, icons, permissions, and much more. You will also find in this file the list of members and their permissions, although Axobot is not able to reinvite members if needed.  
This backup will avoid the most important damage, those little mistakes that can destroy your server as I myself experienced a few years ago. I hope to be able to save what is important to you.

When you load the backup, the bot may not be able to apply some changes. However, it will give you a complete list of what has and hasn't been changed so that you can fix it yourself.

.. warning:: The bot will need as many permissions as possible, which includes: `Manage roles <perms.html#manage-roles>`__, `Manage channels <perms.html#manage-channels>`__, `Manage webhooks <perms.html#manage-webhooks>`__, `Ban members <perms.html#ban-members>`__, `Manage emojis <perms.html#manage-emojis>`__.

Create a backup
---------------

**Syntax:** :code:`backup create`

Creates a file containing as much information as possible on your server, within the limit of the permissions granted to the bot. You will have to keep this file carefully, it will be necessary for you when you will want to restore the backup.

Load a backup
-------------

**Syntax:** :code:`backup load`

Uses the file attached to this message to load a backup, based on the data stored in the file. Be sure to send the file in the same message as the command, so that Axobot can easily find it. If the bot lacks permissions, it will try to skip this step and write it down in the logs. The set of logs is then sent at the end of the procedure.


------------------------
Voice channels managment
------------------------

Give a role to voice users
--------------------------

**Syntax** :code:`config set voice_roles <your roles>`

You can easily give a role to any member joining a voice channel, and revoke it when the member leave the channel. This allows you to create a specific text channel for people talking together, for example.

Create automated voice channels
-------------------------------

Managing a server isn't easy. You often have too many or not enough channels, especially voice channels. This is why the bot has an automated voice channels management system, which will create new voice channels when needed, and delete them when they aren't used anymore.

To do that, you only need to configure a special voice channel where every member joining it will trigger a new channel creation. This can be achieved with the :code:`config set voice_channel <your channel>` command.

Then, the bot needs to know where it should create these new channels. A simple :code:`config set voice_category <your category>` will ask the bot to create its new channels at the bottom of a specific category.

Axobot will take a random name for each new channel, from a random names API, but you can change the name format with the :code:`config set voice_channel_format <new format>` command. Several special keywords exists so you can get some unique names, feel free to use them in your format:

* :code:`{random}` inserts a random surname from randommer.io
* :code:`{minecraft}` inserts a random minecraft entity name
* :code:`{number}` inserts a random number
* :code:`{user}` inserts the Discord name and tag of the user who summoned the channel

If you have more ideas of variables to add, you can suggest them in our Discord support server!

.. warning:: Axobot needs the "`Manage channels <perms.html#manage-channels>`__", "`Move members <perms.html#move-members>`__" and "`Connect <perms.html#connect>`__" permissions in the selected category to create these news channels!

Clear your unusued auto channels
--------------------------------

Axobot will try to delete the channels automatically created once everyone left it. But if, for any reason, you still have some unusued auto voice channels, you can use the super :code:`voice-clean` command to start a big cleanup!

.. note:: Aynone with "`Manage channels <perms.html#manage-channels>`__" permission can use that command!
