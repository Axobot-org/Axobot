====================
Server configuration
====================


--------------
Config options
--------------


Recently, ZBot has features that can be modified per server, to make each server unique. You will find the language of the bot, the activation of certain options (such as the xp system), the list of roles authorized to use certain commands (ban, clear...), the welcome messages, and many other options. 

The list of options continues to grow as development progresses, that's why a website is planned to make server configuration easier.

.. note:: For the curious, know that all the configuration of each server is entirely saved in a MySQL database file, which makes its use easier than a simple txt or csv file.

Watch
-----

**Syntax:** :code:`config see [option]`

The `see` subcommand allows you to see the value of a configuration, with a mini explanatory sentence. If no option is specified, the entire configuration will be displayed in a single message. Note that the bot can suffer a slight latency since this data is stored in an external database.

A detailed list of all options is available `below <#list-of-every-option>`_ .

.. warning:: To display this command correctly, ZBot only needs Embed links permission.


Modify
------

**Syntax:** :code:`config change <option> <value>`

This subcommand allows you to modify the value of an option. Just enter the exact name of the option and its value. A validation message will then be sent if the request has been correctly executed. 

If the value contains several objects, such as a list of roles or channels, they must be separated by commas, like this: :code:`config change clear Admin, Moderators, Special role for Special people`.

.. note:: When the value takes the form of roles, for more comfort you are not obliged to mention them: the exact name or the identifier of the role is enough. The same goes for chanels.



Delete
------

**Syntax:** :code:`config del <option>`

This subcommand can be useful to reset an option to its default value. By executing this command, the option will be deleted and will take the same value as originally.


List of every option
--------------------

* prefix: Character string that will be the bot prefix, for all commands, beginning with the validation message. The prefix must be between 1 and 5 characters long. By default, :code:`!`.
* language: Language of the bot. Currently only the languages :code:`fr` (French) and :code:`en` (English) are available (also you ca try :code:`lolcat` for more fun). The change takes place as soon as the order is validated by the system. Default :code:`fr`.
* clear: List of roles allowed to use the `clear <moderator.html#clear>`_ command. By default, none.
* slowmode: List of roles allowed to use the `slowmode <moderator.html#slowmode>`_ and `freeze <moderator.html#freeze>`_ commands. By default, none.
* mute: List of roles allowed to use the `mute <moderator.html#mute>`_ command. By default, none.
* kick: List of roles allowed to use the `kick <moderator.html#kick>`_ command. By default, none.
* ban: List of roles allowed to use the `ban <moderator.html#ban>`_ command. By default, none.
* warn: List of roles allowed to use the `warn <moderator.html#warn>`_ and `cases <moderator.html#handling-cases>`_ commands. By default, none.
* say: List of roles allowed to use the `say` command. By default, none.
* welcome_channel: List of channels where messages when a member joins/leaves the server will be sent. By default, none.
* welcome: Message sent when a member joins your server. Some variables are usable, enter the `welcome <infos.html#welcome>`_ command to see them.
* leave: Message sent when a member leave your server. Some variables are usable, the same as for the welcome message.
* gived_roles: List of roles automatically given to members when they join the server. It is necessary that the bot is above the roles in question, and that it has the permission "Manage roles".
* bot_news: List of channels to which new bot products will be sent. These are the new bugs found as well as the new features added. None by default.
* modlogs_channel: Channel where all moderation logs (ban, warn, clear...) will be sent.
* save_roles: Boolean indicating if the bot should restore the roles of a member leaving then rejoining the server. All roles below the ZBot role will be redistributed. :code:`False` by default.
* poll_channels: List of channels in which the bot will add the reactions 👍 and 👎 to each message
* enable_xp: Boolean indicating whether the xp system is activated. Default is :code:`True`.
* levelup_msg: Message to send when someone reaches a new XP level. You can use :code:`{level}` variable to include the reached level, and :code:`{user}` to mention the user. Default is :code:`Hey, {user} has just reached **level {level}**! Keep this way!`
* xp_type: Type of XP system to use: :code:`global` if you want to use the accross-server system, common with every other servers which use it, or :code:`mee6` if you want to use the `MEE6 <https://mee6.xyz>`_ levels plugin. Default to :code:`global`.
* noxp_channels: List of text channels where members will not be able to earn any exp. Not necessary if XP is disabled in your server.
* anti_caps_lock: Boolean indicating whether the bot should send a warning message when a message with too much capitalization is sent. Default is True.
* enable_fun: Boolean indicating if the fun part (documentation in preparation) is activated. If so, all commands in this section will be available. Default is :code:`True`.
* membercounter: A voice salon whose name displays the number of members on the server
* anti_raid: Anti-raid protection with some useful features. More information `here <moderator.html#anti-raid>`_. Default level: 0
* vote_emojis: List of emojis that the bot will have to use when there is a voting message. This case may occur when using the vote command, or in a poll channel.
* help_in_dm: Boolean indicating whether the help command message should be sent as a private message, or in the server. If the value is set to :code:`True`, the message will be sent in DM.
* partner_channel: One channel where every partners of the server will be displayed. Default to None.
* partner_color: The color of the partners embeds. Can be hex, integer or common english names. Default to #a713fe.
* partner_role: A role given to every administrator of a partner server. Default to None.



---------------
Partners system
---------------

As a server grows, it is not uncommon to see partnerships formed with other servers. Some may even partner with bots. Zbot therefore offers a system to manage these partnerships in a clean and automatic way. Thanks to this system you can add, edit or remove partners in a few commands, and they will all be displayed in the same place, with the main information about them.

This information on partners is refreshed every 7 hours, starting at 1am (Paris time). It is currently impossible to reload the list yourself, only a Zbot administrator can do so.


Add a partner
-------------

**Syntax:**:code:`partner add <invite>`

Allows you to add a server or bot to your partner list. The invitation must be either a server invitation (starting with discord.gg) or a bot invitation (discordapp.com/oauth). This invitation will be used to synchronize the partner, so make sure it does not expire.


Add a description
-----------------

**Syntax:**:code:`partner description <ID> <new message>`

Adds or modifies the description of a partner. The identifier must be that of the partnership, obtainable via the command `partners list` or under the embed displayed in the partners' lounge.


Change a server invite
----------------------

**Syntax:**:code:`partner invite <ID> [new invite]`

It often happens that for X reason an invitation becomes invalid. Problem: Zbot uses the partner invitation to synchronize partners with the channel. There is therefore a command to quickly change the invitation of a server. 

.. note:: If no new invitation is given in the command, the bot will send you the one currently in use.


List every partners
-------------------

**Syntax:**:code:`partners list`

Lists all the partners that your server currently has. The bot will display the name of the partner, the type (server or bot), and the date of addition. You will even have the list of servers that have added you as a partner!

.. warning:: For a better display of the list, it is recommended to give "`Embed Links <perms.html#embed-links>`_" permission to the bot.

Remove a partner
-----------------

**Syntax:**:code:`partner remove <ID>`

Allows you to remove a partner from the list. You will be asked for a confirmation, to avoid misuse. Once a partner is removed, you must reconfigure it completely if you want to put it back into the channel.