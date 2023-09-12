=============
🔨 Moderation
=============

Like many Discord bots, Axobot allows you to moderate your server in different ways. You will find the classic commands to delete messages, mute, kick out or ban a member, as well as being able to slow down or freeze a chat completely.

Among the features in preparation you will find the members' records as well as the possibility of sending warnings, or a section on automatic moderation.


.. note:: Like most of the features of this bot, the Moderation section is constantly being developed. Feel free to help us by offering suggestions, voting for the best ideas or reporting bugs at our `Discord server <https://discord.gg/N55zY88>`__!

.. warning:: Most of these commands are reserved for certain roles only. To allow roles to use a command, see the `config <onfig.html>`__ command


----
Warn
----

**Syntax:** :code:`warn <user> <message>`:

This command allows you to warn a member, without really sanctioning them. This member will receive this warning by personal message (if they have not disabled them), and the warning will be stored in his logs.

-----------
Mute/Unmute
-----------

.. tip:: Check our `in-depth article <articles/mute.html>`_ to know everything about the mute command: how to configure it in your server, what are the diffenrent ways tomute people, and how to use its commands efficiently!

**Syntax:** :code:`mute <user> [duration] [reason]`

This command mutes a member, preventing them from sending messages. If you configured a muted role, Axobot will give it to the member, and remove it when the mute is over. If you didn't, Axobot will use Discord's "time out" feature, which will prevent the member from sending messages for the duration of the mute.

The duration of the temporary mute is quite flexible: use :code:`XXd` for days, :code:`XXh` for hours and :code:`XXm` for minutes (replacing **XX** by the corresponding number, of course!)

.. warning:: if you use a "muted" role, the role must be placed below the bot role, and the bot must have "`Manage roles <perms.html#manage-roles>`__" (to give the role) permission.

.. note:: Axobot remembers when a member is muted in your server, and only delete this information when someone uses the !unmute command. So, if a member tries to lose his "muted" role by leaving and joining the server, Axobot will give them back his role, even if you removed it manually (without the command)!

**Syntax:** :code:`unmute <user>`

This command unmutes a member, when they already have the muted role. Not necessary when you had specified a duration during the mute, unless you want to stop it prematurely.

**Syntax:** :code:`mute-config`

With this command, Axobot will try to configure automatically the muted role (and create it if needed) with the correct permissions, both in your server and in your channels/categories. Basically, in Discord, the rule is "if a member has any role allowing them to do X, then they will be able to do X, no matter what other roles they have". So Axobot will at first make the muted role disallowing members to send messages in the channels (with the red cross permission), then check every other roles and make sure they don't allow muted members to send messages (so any green check will become a gray tick in the channels permissions).

--------
Slowmode
--------

**Syntax:** :code:`slowmode <seconds>` or :code:`slowmode off`

Slowmode keeps your text channel quiet when excited people have decided to talk a little too fast. More precisely, it prevents members from posting messages too often. The frequency between two consecutive messages from the same member is indicated in the command.

.. note:: The system uses a brand new feature released on September 8th in Discord beta. It therefore is a completely new as in very few bots have it) feature and can be highly integrated into your applications. It is even better than just deleting messages.

-----
Clear
-----

**Syntax:** :code:`clear <number> [parameters]`

This command allows you to efficiently delete messages, with a list of possible parameters for more accuracy. You can thus specify a list of members to check by mentioning them, if it should delete all messages containing files/images, or all containing links or Discord invitations, or even pinned messages. By default, the bot will not delete pinned messages.

Be careful, all specified settings must be validated for the message to be deleted. For example, if you enter :code:`/clear 10 users: @z_runner contains_file: True`, the bot will check in the last ten messages if the message comes from @z_runner AND if the message contains an image.

If you enter :code:`/clear 25 contains_url: True`, the bot will clear the last 25 messages if they contains a link AND if they're not pinned, no matter the author.

If you enter :code:`/clear 1000 users: @z_runner @Axobeta#4940`, the bot will delete all (not pinned) messages contained in the last 1000 messages of the channel AND written by @z_runner OR Axobeta#4940.

.. warning:: The permissions "`Manage messages <perms.html#manage-messages>`__" and "`Read messages history <perms.html#read-message-history>`__" are required.

**Syntax:** :code:`destop <message>`

If you don't know how many messages you want to delete, but instead want to delete all of them until a certain message, you can use this command. The "message" argument can be either a message ID (from the same channel) or a message url (from any channel of your server). Permissions needed for users and bot are the same as the clear command.

----
Kick
----

**Syntax:** :code:`kick <user> [reason]`

The kick allows you to eject a member from your server. This member will receive a personal message from the bot to alert them of his expulsion, with the reason for the kick if it's specified.
It is not possible to cancel a kick. The only way to get a member back is to send them an invitation (see the `invite <infos.html#invite>`__ command) via another server.

.. warning:: For the command to succeed, the bot must have "`Kick members <perms.html#kick-members>`__" permissions and be placed higher than the highest role of that member.


-------
Softban
-------

**Syntax:** :code:`softban <user> [reason]`

This command allows you to expel a member from your server, such as kick. But in addition, it will delete all messages posted by this member during the last 7 days. This is what explains its name: the bot bans a member by asking Discord to delete the messages (which is not possible with a kick), then unban immediately the member.

.. warning:: For this command, the bot needs "`Ban members <perms.html#ban-members>`__" permission, and you need to have a role to use the "`kick <#kick>`__" command

---------
Ban/Unban
---------

**Syntax:** :code:`ban <user> [duration] [days_to_delete] [reason]`

The ban allows you to instantly ban a member from your server. This means that the member will be ejected, and will not be able to return before being unbanned by a moderator. The 'days_to_delete' option represents the number of days worth of messages to delete from the user in the guild, bewteen 0 and 7 (0 by default)

The duration of the tempban is the same as for the tempmute: use :code:`XXd` for days, :code:`XXh` for hours and :code:`XXm` for minutes (replacing **XX** by the corresponding number, of course!)

To cancel this action, use the Discord interface or the `unban <#unban>`__ command. The member will nevertheless have to decide for themselves if he wishes to return to your server.



**Syntax:** :code:`unban <user> [reason]`

This command allows you to revoke a ban, whether it was made via this bot or not. Just fill in the exact name or the identifier of the member you wish to be unbanned so that the bot can find the member you choose in the list of banned members for the member in question.

The persons authorized to use this command are the same as for the `ban <#ban>`__ command(see the :code:`config` command).

.. warning:: For both commands to succeed, the bot must have "`Ban members <perms.html#ban-members>`__" permissions (as well as be placed higher than the highest role of the member to ban).

----------------
Banlist/Mutelist
----------------

**Syntax:** :code:`banlist` *or* :code:`mutelist`

If you mute and ban so many people that you don't remember the exact list, and you have the laziness to look in your server options, this command will be happy to refresh your memory without too much effort.

The 'reasons' argument allows you to display or not the reasons for the sanction.

.. note:: Note that this command is only available for your server administrators for `banlist` and your moderators for `mutelist`. Ah, and Discord also likes privacy, so the bot can't read this list if he doesn't have permission to "`ban people <perms.html#ban-members>`__".

--------------
Handling cases
--------------

View list
---------

**Syntax:** :code:`cases list <user>`

If you want to know the list of cases/logs that a member has in this server, you can use this command. Note that to select a member, you must either notify them, retrieve their ID or write their full name.

The persons authorized to use this command are the same as for the `warn <#warn>`__ command.

.. warning:: The list of cases is returned in an embed, which means that the bot must have "`Embed Links <perms.html#embed-links>`__" permission.


Search for a case
-----------------

**Syntax:** :code:`cases search <case ID>`

This command allows you to search for a case from its identifier. The identifiers are unique for the whole bot, so you can't see them all.

.. warning:: The case is returned in an embed, which means that the bot must have "`Embed Links <perms.html#embed-links>`__" permission to send it correctly.

Edit Reason
-----------

**Syntax:** :code:`cases reason <case ID> <new reason>`

If you want to edit the reason for a case after creating it, you will need to use this command. Simply retrieve the case ID and enter the new reason. There is no way to go back, so be sure to make no mistake!

The persons authorized to use this command are the same as for the `warn <#warn>`__ command.


Remove case
-----------

**Syntax:** :code:`cases (remove|clear|delete) <case ID>`

This is the only way to delete a case from the logs for a user. Just to make sure you don't forget the command name, there are three aliases for the same command.

The locker will be deleted forever, and forever can be very, very long. So be sure you're not mistaken, there's no backup!

The persons authorized to use this command are the same as for the `warn <#warn>`__ command.

---------
Anti-raid
---------

*Not a command, but a server option.*

This option allows you to moderate the entry of your server, with several levels of security. You can enable it with the :code:`/config set anti_raid` command followed by the level you want.

Here is the list of levels:

* None
    * no filter
* Smooth
    * kick users with invitations in their nickname
    * time-out for 20min users sending 30 mentions in a short time
* Careful
    * kick accounts created less than 2 hours before
    * time-out for 30min users sending 20 mentions in a short time
    * time-out for 15min users sending 10 mentions in a short time
* High
    * ban users with invitations in their nickname for a week
    * ban accounts created less than 1 hour before for a week
    * kick accounts created less than 12h before
    * kick users sending 20 mentions in a short time
    * time-out for 30min users sending 10 mentions in a short time
* Extreme
    * ban accounts created less than 3 hours before for a week
    * ban accounts created less than 1h before for 2 weeks
    * ban users sending 20 mentions in a short time for 2 week
    * kick accounts created less than 24h before
    * kick users sending 15 mentions in a short time
    * time-out for 1h users sending 10 mentions in a short time

.. note:: Note that the levels are cumulative: for example level 3 will also have the specificities of levels 1 and 2

.. warning:: The bot must have access to "`Kick members <perms.html#kick-members>`__" and "`Ban members <perms.html#ban-members>`__" permissions

---------
Anti-scam
---------

**How does it work?**

Axobot has an advanced scam message detection system, involving a `highly trained AI <articles/scam-detector.html>`__ that has been conscientiously built over several months. This allows you to automatically filter and remove any messages that are dangerous to your members, such as Nitro scams or other suspicious links.

When Axobot is certain that a message is dangerous, it will delete the message immediately and send a log to the logs channel if you have configured it. If Axobot detects a "probably dangerous" message, it will not take any action but will send you an alert in this same logs channel. So make sure you have configured an antiscam logs channel if you enable this feature.

.. note:: Messages that are too short, or sent by moderators (members with "manage messages" or "manage server" permissions) or bots will not be monitored by this system.


**List of commands:**
:code:`antiscam enable` or :code:`antiscam disable` to enable/disable the system (require "manage server" permission)
:code:`modlogs enable antiscam` to enable antiscam logs in a channel (require "manage server" permission)
:code:`antiscam test` followed by any text to test how dangerous this text may be
:code:`antiscam report` followed by any text or message link to report a malicious message to the bot team

.. warning:: By enabling this feature, you allow Axobot to read and analyze all messages on your server, and messages considered suspicious may be anonymized and stored in our database for better detection. You are solely responsible for notifying your community of this.

-----------
Server logs
-----------

To help you moderate your server and keep track of what's going on, Axobot has a logging system somewhat similar to the Discord one. You can decide to track one or more types of "events" in a channel, and Axobot will send a message there whenever something new happens. For example, it is possible to have a log at every ban or unban, or when a member changes role, etc.

.. note:: The bot has very few different types of logs at the moment, but there are plans to add many more in the next updates!

How to setup logs
-----------------

You can enable one or more logs types in a channel by using the :code:`modlogs enable <logs> [channel]` in the channel you want them to appear in (or in another channel by mentionning it). In the same way, use :code:`modlogs disable <logs> [channel]` to disable a kind of logs in the current channel. Please note that you can use the keyword "all" as a log type to enable or disable all at the same time.

To see in Discord which logs exists and which ones you have enabled in your server, use the command :code:`modlogs list`. You can also use this command followed by a channel mention or ID to see which logs are enabled in a specific channel.

Types of logs
-------------

* **antiraid:** A new member is kicked or banned by the raid detection system
* **antiscam:** A message is flagged as a potential scam by the antiscam AI
* **bot_warnings:** Axobot couldn't do its job due to an external factor (like a missing permission)
* **clear**: Some messages have been deleted by the :code:`clear` command
* **discord_invite:** A member just sent a message containing one or more Discord server invite link
* **ghost_ping:** A member deleted a message containing a user mention right after sending it
* **member_avatar:** A member changes its guild avatar
* **member_ban:** A user is banned from your server
* **member_join:** A member joins your server
* **member_kick:** A member is kicked from your server
* **member_leave:** A member leaves your server
* **member_nick:** A member has its nickname changed
* **member_roles:** A member gets or loses roles
* **member_timeout:** A member is set on timeout by one of your moderators
* **member_unban:** A user is unbanned from your server
* **member_verification:** A user has been verified by the Discord community rules screen (if enabled in your server)
* **member_warn:** A member has been warned by one of your moderators with the :code:`warn` command
* **message_update:** A message is edited
* **message_delete:** A message is deleted
* **moderation_case:** A moderation case has been edited or deleted with the :code:`case` command
* **role_creation:** A role is created
* **role_deletion:** A role is deleted
* **role_update:** A role has been edited
* **server_update:** The server has been edited (icon, name, or features)
* **slowmode:** A channel has been put on slowmode with the :code:`slowmode` command
* **ticket_creation:** A `ticket <tickets.html>`__ has been opened
* **user_update:** A user profile has been otherwise edited (usually badges)


--------------
Miscellaneaous
--------------


Emoji Manager
-------------

With this command, you can become the undisputed master of the Emojis and handle them all as you please. You can even do something that no one has ever done before, a beta exclusivity straight out of the Discord labs: restrict the use of certain emojis to certain roles! **YES!** It's possible! Come on, let's not waste any time, here's the list of commands currently available :

* :code:`emoji rename <emoji> <new name>` : renames your emoji, without going through the Discord interface. No more complicated thing.

* :code:`emoji restrict <emoji> <roles>` : restrict the use of an emoji to certain roles. Members who do not have this role will simply not see the emoji in the list. Note that there is no need to mention, just put the identifier or the name.

* :code:`emoji clear <message ID> [emoji]` : instantly removes reactions from a message. This message must be indicated via its identifier, and belong to the same chat as the one where the command is used. If no emoji is specified, every reaction will be deleted. The bot must have "`Manage Messages <perms.html#manage-messages>`__" and "`Read Message History <perms.html#read-message-history>`__" permissions.

* :code:`emojis list [page=1]` : lists all the server's emojis (each page has max 50 emojis), in an embed, and indicates if some of them are restricted to certain roles. The bot must have "`Embed Links <perms.html#embed-links>`__" permission.



.. warning:: The bot needs the `Manage expressions <perms.html#manage-expressions>`__ permission to edit these pretty little pictures. And you, you need the "Manage expressions" permission to use these commands.


Role Manager
------------

Nice command that allows you to do different things with the server roles (other subcommands will be created later). The permissions required to execute them depend on the subcommands, ranging from anyone to the administrator. If you have any ideas or other suggestions, feel free to contact us via `our Discord server <https://discord.gg/N55zY88>`__, or in PM at the bot!

* :code:`role color <role> <colour>` (alias `role colour`): Changes the color of the given role. The color must be in hexadecimal form, although some common names are accepted (red, blue, gold...). To remove the color, use the name `default`. Please check notes 1. and 2.

* :code:`role grant <role> <user(s) | role(s)>`: Give a role to a list of people. You can target as many users or roles as you want, so for example to target your friends Joe and Jack, plus the Admin role, use :code:`role give superRole Joe Jack Admin`. Please check note 2. To avoid spamming the Discord API, Axobot also limit how many users you can affect by this command, and will tell you if this limit is reached.

* :code:`role temporary-grant <role> <user> <duration>`: Give a role to a user for a certain amount of time. The duration must be in the format `1d 2h 3m` (days, hours, minutes, seconds). Please check notes 1 and 2.

* :code:`role remove <role> <user(s) | role(s)>`: Same as above, but instead of giving them, it takes them away. Please check note 2.

* :code:`role list <role>`: List every members who are in a specific role, if this number is under 200. The bot must have "`Embed Links <perms.html#embed-links>`__" permission to display the result. Please check note 2.

* :code:`role server-list`: Liste every role of your server, with the members count. The bot must have "`Embed Links <perms.html#embed-links>`__" permission to display the result. Please check note 2.

.. warning:: (1) The bot need the "`Manage roles <perms.html#manage-roles>`__" permission, also his highest role need to be higher than the role he's trying to edit.
    (2) You need to have the "`Manage roles <perms.html#manage-roles>`__" permission (or be an administrator) to use this command. Else, Axobot won't react.


Unhoist members
---------------

People like to put strange characters in their nicknames to appear at the top of the membership list. With this command you will be able to put an end to this habit. Simply type the command without argument to remove all non-alphabetic characters (a-z A-Z 0-9) at the beginning of the nickname, and you can give your own characters via an argument. Easy, isn't it?

**Syntax:** :code:`unhoist [characters]`

.. warning:: It is necessary that the bot has "Manage nicknames" permission, and that its role is above the roles of the members to be renamed.
