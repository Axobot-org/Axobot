==========
Moderation
==========

Like many Discord bots, ZBot allows you to moderate your server in different ways. You will find the classic commands to delete messages, mute, kick out or ban a member, as well as being able to slow down or freeze a chat completely. 

Among the features in preparation you will find the members' records as well as the possibility of sending warnings, or a section on automatic moderation.


.. note:: Like most of the features of this bot, the Moderation section is constantly being developed. Feel free to help us by offering suggestions, voting for the best ideas or reporting bugs at our `Discord server <https://discord.gg/N55zY88>`_!

.. warning:: Most of these commands are reserved for certain roles only. To allow roles to use a command, see the `config <onfig.html>`_ command


----
Warn
----

**Syntax:** :code:`warn <user> <message>`:

This command allows you to warn a member, without really sanctioning him. This member will receive this warning by personal message (if they have not disabled them), and the warning will be stored in his logs.

-----------
Mute/Unmute
-----------

**Syntax:** :code:`mute <user> [duration] [reason]`

This command mutes a member, preventing them from typing. 

The principle is to assign the *muted* role to the member, in order to distinguish him from the others. Simply configure the permissions to have the "send messages" option disabled in your channels. And if configuring the role is too much work for you, you can ask the bot to try to setup it automatically with the :code:`mute-config` command (see below).

The duration of the tempmute is quite flexible: use :code:`XXd` for days, :code:`XXh` for hours and :code:`XXm` for minutes (replacing **XX** by the corresponding number, of course!)

.. warning:: The muted role must be placed below the bot role, and the bot must have "`Manage roles <perms.html#manage-roles>`_" (to give the role) permission.

.. note:: Zbot remembers when a member is muted in your server, and only erases this information when someone uses the !unmute command. So, if a member tries to lose his "muted" role by leaving and joining the server, Zbot will give him back his role, even if you removed it manually (without the command)!

**Syntax:** :code:`unmute <user>`

This command unmutes a member, when they already have the muted role. Not necessary when you had specified a duration during the mute, unless you want to stop it prematurely.

**Syntax:** :code:`mute-config`

With this command, Zbot will try to configure automatically the muted role (and create it if needed) with the correct permissions, both in your server and in your channels/categories. Basically, in Discord, the rule is "if a member has any role allowing them to do X, then they will be able to do X, no matter what other roles they have". So Zbot will at first make the muted role disallowing members to send messages in the channels (with the red cross permission), then check every other roles and make sure they don't allow muted members to send messages (so any green check will become a gray tick in the channels permissions).

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

This command allows you to efficiently delete messages, with a list of possible parameters for more accuracy. You can thus specify a list of members to check by mentioning them, `+i` to delete all messages containing files/images, `+l` for those containing links or Discord invitations, `+p` for pinned messages. By default, the bot will not delete pinned messages.

Be careful, all specified settings must be validated for the message to be deleted. For example, if you enter :code:`clear 10 @Z_runner#7515 +i`, the bot will check in the last ten messages if the message comes from Z_runner#7515 AND if the message contains an image. 

If you enter :code:`clear 25 -p +l`, the bot will clear the last 25 messages if they contains a link AND if they're not pinned, no matter the author.

If you enter :code:`clear 13 -p -i @Z_runner#7515`, the bot will clear the last 13 messages if they are not pinned AND if they does not contain any file/image AND if the author is Z_runner#7515.

If you enter :code:`clear 1000 @Z_runner#7515 @ZBot beta#4940`, the bot will delete all messages contained in the last 1000 messages of the channel AND written by Z_runner#7515 OR ZBot beta#4940 

.. warning:: The permissions "`Manage messages <perms.html#manage-messages>`_" and "`Read messages history <perms.html#read-message-history>`_" are required.

**Syntax:** :code:`destop <message>`

If you don't know how many messages you want to delete, but instead want to delete all of them until a certain message, you can use this command. The "message" argument can be either a message ID (from the same channel) or a message url (from any channel of your server). Permissions needed for users and bot are the same as the clear command.

----
Kick
----

**Syntax:** :code:`kick <user> [reason]`

The kick allows you to eject a member from your server. This member will receive a personal message from the bot to alert him of his expulsion, with the reason for the kick if it's specified.
It is not possible to cancel a kick. The only way to get a member back is to send him an invitation (see the `invite <infos.html#invite>`_ command) via another server.

.. warning:: For the command to succeed, the bot must have "`Kick members <perms.html#kick-members>`_" permissions and be placed higher than the highest role of that member.


-------
Softban
-------

**Syntax:** :code:`softban <user> [reason]`

This command allows you to expel a member from your server, such as kick. But in addition, it will delete all messages posted by this member during the last 7 days. This is what explains its name: the bot bans a member by asking Discord to delete the messages (which is not possible with a kick), then unban immediately the member.

.. warning:: For this command, the bot needs "`Ban members <perms.html#ban-members>`_" permission, and you need to have a role to use the "`kick <#kick>`_" command

---------
Ban/Unban
---------

**Syntax:** :code:`ban <user> [duration] [days_to_delete] [reason]`

The ban allows you to instantly ban a member from your server. This means that the member will be ejected, and will not be able to return before being unbanned by a moderator. The 'days_to_delete' option represents the number of days worth of messages to delete from the user in the guild, bewteen 0 and 7 (0 by default)

The duration of the tempban is the same as for the tempmute: use :code:`XXd` for days, :code:`XXh` for hours and :code:`XXm` for minutes (replacing **XX** by the corresponding number, of course!)

To cancel this action, use the Discord interface or the `unban <#unban>`_ command. The member will nevertheless have to decide for himself if he wishes to return to your server.



**Syntax:** :code:`unban <user> [reason]`

This command allows you to revoke a ban, whether it was made via this bot or not. Just fill in the exact name or the identifier of the member you wish to be unbanned so that the bot can find the member you choose in the list of banned members for the member in question. 

The persons authorized to use this command are the same as for the `ban <#ban>`_ command(see the :code:`config` command). 

.. warning:: For both commands to succeed, the bot must have "`Ban members <perms.html#ban-members>`_" permissions (as well as be placed higher than the highest role of the member to ban).

----------------
Banlist/Mutelist
----------------

**Syntax:** :code:`banlist` *or* :code:`mutelist`

If you mute and ban so many people that you don't remember the exact list, and you have the laziness to look in your server options, this command will be happy to refresh your memory without too much effort.

The 'reasons' argument allows you to display or not the reasons for the sanction.

.. note:: Note that this command will be deleted after 20 seconds, because privacy is private, and because we like privacy, it is only available for your server administrators for `banlist` and your moderators for `mutelist`. Ah, and Discord also likes privacy, so the bot can't read this list if he doesn't have permission to "`ban people <perms.html#ban-members>`_".

--------------
Handling cases
--------------

View list
---------

**Syntax:** :code:`cases list <user>`

If you want to know the list of cases/logs that a member has in this server, you can use this command. Note that to select a member, you must either notify him/her, retrieve his/her ID or write his/her full name.

The persons authorized to use this command are the same as for the `warn <#warn>`_ command.

.. warning:: The list of cases is returned in an embed, which means that the bot must have "`Embed Links <perms.html#embed-links>`_" permission.


Search for a case
-----------------

**Syntax:** :code:`cases search <case ID>`

This command allows you to search for a case from its identifier. The identifiers are unique for the whole bot, so you can't see them all. However, the ZBot support team has access to all the cases (without being able to modify them)

.. warning:: The case is returned in an embed, which means that the bot must have "`Embed Links <perms.html#embed-links>`_" permission to send it correctly.

Edit Reason
-----------

**Syntax:** :code:`cases reason <case ID> <new reason>`

If you want to edit the reason for a case after creating it, you will need to use this command. Simply retrieve the case ID and enter the new reason. There is no way to go back, so be sure to make no mistake!

The persons authorized to use this command are the same as for the `warn <#warn>`_ command.


Remove case
-----------

**Syntax:** :code:`cases (remove|clear|delete) <case ID>`

This is the only way to delete a case from the logs for a user. Just to make sure you don't forget the command name, there are three aliases for the same command.

The locker will be deleted forever, and forever can be very, very long. So be sure you're not mistaken, there's no backup!

The persons authorized to use this command are the same as for the `warn <#warn>`_ command.

---------
Anti-raid
---------

*Not a command, but a server option.*

This option allows you to moderate the entry of your server, with several levels of security. Here is the list of levels: 

* 0 (None): no filter
* 1 (Smooth): kick members with invitations in their nickname
* 2 (Careful): kick accounts created less than 15min before
* 3 (High): ban members with invitations in their nickname, and kick accounts created less than 45min before
* 4 ((╯°□°）╯︵ ┻━┻): ban members created less than 1 hour before, and kick those created less than 2 hours before

.. note:: Note that the levels are cumulative: level 3 will also have the specificities of levels 1 and 2

.. warning:: The bot must have access to "`Kick members <perms.html#kick-members>`_" and "`Ban members <perms.html#ban-members>`_" permissions


---------------------
Anti-bot verification
---------------------

**How does it work?**

The verification system works with a simple command and a role, and filters most of the selfbots that attack your servers.

Zbot uses a list of random questions he asks the user to test it, and if the answer is correct, the user is removed from the defined role (if he has it). The command to type to "verify" is :code:`verify`, and to define which role to remove, it is the configuration option `verification_role`, configurable using the command :code:`config change verification_role <role>`.

It is recommended to give this role to all new members via the `welcome_roles` option, then block access to the server for this role, in order to force the new members to check themselves.


**List of commands:**
:code:`verify`: ask a question to check the member
:code:`config change verification_role <role>>` configures the role to be removed from the verified members


.. warning:: For this system, the bot **must** have "`Manage Roles <perms.html#manage-roles>`_" permission. The roles to be removed **must** also be lower than the role of Zbot in your server hierarchy (Server Settings > Roles tab).



--------------
Miscellaneaous
--------------


Emoji Manager
-------------

With this command, you can become the undisputed master of the Emojis and handle them all as you please. You can even do something that no one has ever done before, a beta exclusivity straight out of the Discord labs: restrict the use of certain emojis to certain roles! **YES!** It's possible! Come on, let's not waste any time, here's the list of commands currently available :

* :code:`emoji rename <emoji> <new name>` : renames your emoji, without going through the Discord interface. No more complicated thing.

* :code:`emoji restrict <emoji> <roles>` : restrict the use of an emoji to certain roles. Members who do not have this role will simply not see the emoji in the list. Note that there is no need to mention, just put the identifier or the name.

* :code:`emoji clear <message ID> [emoji]` : instantly removes reactions from a message. This message must be indicated via its identifier, and belong to the same chat as the one where the command is used. If no emoji is specified, every reaction will be deleted. The bot must have "`Manage Messages <perms.html#manage-messages>`_" and "`Read Message History <perms.html#read-message-history>`_" permissions.

* :code:`emojis list [page=1]` : lists all the server's emojis (each page has max 50 emojis), in an embed, and indicates if some of them are restricted to certain roles. The bot must have "`Embed Links <perms.html#embed-links>`_" permission.



.. warning:: The bot needs the `Manage Emojis <perms.html#manage-emojis>`_ permission to edit these pretty little pictures. And you, you need Administrator permission to use these commands.


Role Manager
------------

Nice command that allows you to do different things with the server roles (other subcommands will be created later). The permissions required to execute them depend on the subcommands, ranging from anyone to the administrator. If you have any ideas or other suggestions, feel free to contact us via `our Discord server <https://discord.gg/N55zY88>`_, or in PM at the bot!

* :code:`role color <role> <colour>` (alias `role colour`): Changes the color of the given role. The color must be in hexadecimal form, although some common names are accepted (red, blue, gold...). To remove the color, use the name `default`. Please check notes 1. and 2.

* :code:`role give <role> <user(s) | role(s)>`: Give a role to a list of people. You can target as many users or roles as you want, so for example to target your friends Joe and Jack, plus the Admin role, use :code:`role give superRole Joe Jack Admin`. Please check note 2.

* :code:`role remove <role> <user(s) | role(s)>`: Same as above, but instead of giving them, it takes them away. Please check note 2.

* :code:`role list <role>`: List every members who are in a specific role, if this number is under 200. The bot must have "`Embed Links <perms.html#embed-links>`_" permission to display the result. Please check note 2.

* :code:`role server-list`: Liste every role of your server, with the members count. The bot must have "`Embed Links <perms.html#embed-links>`_" permission to display the result. Please check note 2.

.. warning:: (1) The bot need the "`Manage roles <perms.html#manage-roles>`_" permission, also his highest role need to be higher than the role he's trying to edit.
    (2) You need to have the "`Manage roles <perms.html#manage-roles>`_" permission (or be an administrator) to use this command. Else, Zbot won't react.


Unhoist members
---------------

People like to put strange characters in their nicknames to appear at the top of the membership list. With this command you will be able to put an end to this habit. Simply type the command without argument to remove all non-alphabetic characters (a-z A-Z 0-9) at the beginning of the nickname, and you can give your own characters via an argument. Easy, isn't it?

**Syntax:** :code:`unhoist [characters]`

.. warning:: It is necessary that the bot has "Manage nicknames" permission, and that its role is above the roles of the members to be renamed.
