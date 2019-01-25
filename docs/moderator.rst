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

----
Mute
----

**Syntax:** :code:`mute <user> [reason]`

This command mutes a member, preventing them from typing. 

The principle is to assign the *muted* role to the member, in order to distinguish him from the others. Simply configure the server permissions to have the "send messages" option disabled. And even if you don't, the bot will delete messages from recalcitrant mute members! 

.. warning:: The muted role must be placed below the bot role, and the bot must have "`Manage roles <perms.html#manage-roles>`_" (to give the role) and "`Manage messages <perms.html#manage-messages>`_" (to delete messages) permissions.

--------
Slowmode
--------

**Syntax:** :code:`slowmode <seconds>` or :code:`slowmode off`

Slowmode keeps your text channel quiet when excited people have decided to talk a little too fast. More precisely, it prevents members from posting messages too often. The frequency between two consecutive messages from the same member is indicated in the command.  

.. note:: The system uses a brand new feature released on September 8th in Discord beta. It therefore is a completely new as in very few bots have it) feature and can be highly integrated into your applications. It is even better than just deleting messages.

------
Freeze
------

**Syntax:** :code:`freeze (on|off)`

The freeze command is made to completely freeze a chat that has gotten too hot, so that nobody can talk before being cooled. To break the ice, just turn it off.
People authorized to use the freeze command are the same as the ones who can use `slowmode <#slowmode>`_ (see the `config <config.html>`_ command). 

.. warning:: The bot needs "`Manage messages <perms.html#manage-messages>`_" permission in order to delete messages from chatty members. In addition, members authorized to trigger the freeze are immune to this effect.


-----
Clear
-----

**Syntax:** :code:`clear <number> [parameters]`

This command allows you to efficiently delete messages, with a list of possible parameters for more accuracy. You can thus specify a list of members to check by mentioning them, `+i` to delete all messages containing files/images, `+l` for those containing links or Discord invitations, `+p` for pinned messages. By default, the bot will not delete pinned messages

Be careful, all specified settings must be validated for the message to be deleted. For example, if you enter :code:`clear 10 @Z_runner#7515 +i`, the bot will check in the last ten messages if the message comes from Z_runner#7515 AND if the message contains an image. 

If you enter :code:`clear 25 -p +l`, the bot will check in the last 25 messages if the message contains a link AND if the message is not pinned, no matter the author.

If you enter :code:`clear 13 -p -i @Z_runner#7515`, the bot will check in the last 13 messages if the message is not pinned AND if the message does not contain any file/image AND if the author is Z_runner#7515.

If you enter :code:`clear 1000 @Z_runner#7515 @ZBot beta#4940`, the bot will delete all messages contained in the last 1000 messages of the channel AND written by Z_runner#7515 OR ZBot beta#4940 

.. warning:: The permissions "`Manage messages <perms.html#manage-messages>`_" and "`Read messages history <perms.html#read-message-history>`_" are required.

-----
Purge
-----

**Syntax:** :code:`purge`

This command allows you to clean the place a little, by deleting all the messages in a channel, and leaving only the pinned messages, no matter who wrote them. Purge is limited to 10,000 messages per command, in order to avoid overloading the bot.A confirmation request will be sent to you, to avoid any false manipulation.

The roles allowed to use this command are the same as for the `clear <#clear>`_ command.

.. warning:: The permissions "`Manage messages <perms.html#manage-messages>`_" and "`Read messages history <perms.html#read-message-history>`_" are required.


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

---
Ban
---

**Syntax:** :code:`ban <user> [reason]`

The ban allows you to instantly ban a member from your server. This means that the member will be ejected, and will not be able to return before being unbanned by a moderator.

To cancel this action, use the Discord interface or the `unban <#unban>`_ command. The member will nevertheless have to decide for himself if he wishes to return to your server.

.. warning:: For the command to succeed, the bot must have "`Ban members <perms.html#ban-members>`_" permissions and be placed higher than the highest role of that member.

-----
Unban
-----

**Syntax:** :code:`unban <user> [reason]`

This command allows you to revoke a ban, whether it was made via this bot or not. Just fill in the exact name or the identifier of the member you wish to be unbanned so that the bot can find the member you choose in the list of banned members for the member in question. 

The persons authorized to use this command are the same as for the `ban <#ban>`_ command(see the :code:`config` command). 

.. warning:: For the command to succeed, the bot must have "`Ban members <perms.html#ban-members>`_" permissions.

-------
Banlist
-------

**Syntax:** :code:`banlist`

If you ban so many people that you don't remember the exact list, and you have the laziness to look in your server options, this command will be happy to refresh your memory without too much effort.

The 'reasons' argument allows you to display or not the reasons for the bans.

.. note:: Note that this command will be deleted after 15 minutes, because privacy is private, and because we like privacy, it is only available for your server administrators. Ah, and Discord also likes privacy, so the bot can't read this list if he doesn't have permission to "`ban people <perms.html#ban-members>`_".

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
* 2 (Careful): kick accounts created less than 1min before
* 3 (High): ban members with invitations in their nickname, and kick accounts created less than 5min before
* 4 ((╯°□°）╯︵ ┻━┻): ban members created less than 3min before, and kick those created less than 10min before

.. note:: Note that the levels are cumulative: level 3 will also have the specificities of levels 1 and 2

.. warning:: The bot must have access to "`Kick members <perms.html#kick-members>`_" and "`Ban members <perms.html#ban-members>`_" permissions



--------------
Miscellaneaous
--------------


Emoji Manager
-------------

With this command, you can become the undisputed master of the Emojis and handle them all as you please. You can even do something that no one has ever done before, a beta exclusivity straight out of the Discord labs: restrict the use of certain emojis to certain roles! **YES!** It's possible! Come on, let's not waste any time, here's the list of commands currently available :

* :code:`emoji rename <emoji> <new name>` : renames your emoji, without going through the Discord interface. No more complicated thing

* :code:`emoji restrict <emoji> <roles>` : restrict the use of an emoji to certain roles. Members who do not have this role will simply not see the emoji in the list. Note that there is no need to mention, just put the identifier or the name.

* WIP...


..warning:: The bot needs the `Manage Emojis <perms.html#manage-emojis>`_ permission to edit these pretty little pictures. And you, you need Administrator permission to use these commands.