=============
Server config
=============

Recently, ZBot has features that can be modified per server, to make each server unique. You will find the language of the bot, the activation of certain options (such as the xp system), the list of roles authorized to use certain commands (ban, clear...), the welcome messages, and many other options. 

The list of options continues to grow as development progresses, that's why a website is planned to make server configuration easier.

.. note:: For the curious, know that all the configuration of each server is entirely saved in a MySQL database file, which makes its use easier than a simple txt or csv file.

-----
Watch
-----

**Syntax:** :code:`config see [option]`

The `see` subcommand allows you to see the value of a configuration, with a mini explanatory sentence. If no option is specified, the entire configuration will be displayed in a single message. Note that the bot can suffer a slight latency since this data is stored in an external database.

A detailed list of all options is available `below <#list-of-every-option>`_ .

.. warning:: To display this command correctly, ZBot only needs Embed links permission.


------
Modify
------

**Syntax:** :code:`config change <option> <value>`

This subcommand allows you to modify the value of an option. Just enter the exact name of the option and its value. A validation message will then be sent if the request has been correctly executed. 

If the value contains several objects, such as a list of roles or channels, they must be separated by commas, like this: :code:`config change clear Admin, Moderators, Special role for Special people`.

.. note:: When the value takes the form of roles, for more comfort you are not obliged to mention them: the exact name or the identifier of the role is enough. The same goes for chanels.


------
Delete
------

**Syntax:** :code:`config del <option>`

This subcommand can be useful to reset an option to its default value. By executing this command, the option will be deleted and will take the same value as originally.


--------------------
List of every option
--------------------

* prefix: Character string that will be the bot prefix, for all commands, beginning with the validation message. The prefix must be between 1 and 5 characters long. By default, :code:`!`.
* language: Language of the bot. Currently only the languages :code:`fr` (French) and :code:`en` (English) are available. The change takes place as soon as the order is validated by the system. Default :code:`fr`.
* clear: List of roles allowed to use the `clear <moderator.html#clear>`_ command. By default, none.
* slowmode: List of roles allowed to use the `slowmode <moderator.html#slowmode>`_ and `freeze <moderator.html#freeze>`_ commands. By default, none.
* mute: List of roles allowed to use the `mute <moderator.html#mute>`_ command. By default, none.
* kick: List of roles allowed to use the `kick <moderator.html#kick>`_ command. By default, none.
* ban: List of roles allowed to use the `ban <moderator.html#ban>`_ command. By default, none.
* warn: List of roles allowed to use the `warn <moderator.html#warn>`_ and `cases <moderator.html#handling-cases>`_ commands. By default, none.
* say: List of roles allowed to use the `say` command. By default, none.
* hunter: List of text channels in which the *Hunter* game is activated (documentation to come). By default, none.
* welcome_channel: List of channels where messages when a member joins/leaves the server will be sent. By default, none.
* welcome: Message sent when a member joins your server. Some variables are usable, enter the `welcome <infos.html#welcome>`_ command to see them.
* leave: Message sent when a member leave your server. Some variables are usable, the same as for the welcome message.
* gived_roles: List of roles automatically given to members when they join the server. It is necessary that the bot is above the roles in question, and that it has the permission "Manage roles".
* bot_news: List of channels to which new bot products will be sent. These are the new bugs found as well as the new features added. None by default.
* modlogs_channel: Channel where all moderation logs (ban, warn, clear...) will be sent.
* save_roles: Boolean indicating if the bot should restore the roles of a member leaving then rejoining the server. All roles below the ZBot role will be redistributed. :code:`False` by default.
* poll_channels: List of channels in which the bot will add the reactions 👍 and 👎 to each message
* enable_xp: Boolean indicating whether the xp system is activated (documentation in preparation). Default is :code:`True`.
* anti_caps_lock: Boolean indicating whether the bot should send a warning message when a message with too much capitalization is sent. Default is True.
* enable_fun: Boolean indicating if the fun part (documentation in preparation) is activated. If so, all commands in this section will be available. Default is :code:`True`.
* membercounter: A voice salon whose name displays the number of members on the server
* anti_raid: Anti-raid protection with some useful features. More information `here <moderator.html#anti-raid>`_. Default level: 0
* vote_emojis: List of emojis that the bot will have to use when there is a voting message. This case may occur when using the vote command, or in a poll channel.
* help_in_dm: Boolean indicating whether the help command message should be sent as a private message, or in the server. If the value is set to :code:`True`, the message will be sent in DM.