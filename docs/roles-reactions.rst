===============
Roles reactions
===============

The reaction role system is increasingly used in Discord servers because of its simplicity. It allows your users to obtain or withdraw a role by simply clicking on a reaction. It is faster than a command to enter, more ergonomic, and it allows a better presentation of the obtainable roles... what more could you ask for?

To make it as easy as possible for users and moderators to use these reactions, we have tried to make it as easy as possible for you to configure this system.

-------------------------
Add and remove a reaction
-------------------------

**Syntax:** :code:`roles_react add <emoji> <role> [description]`

**Syntax:** :code:`roles_react remove <emoji>`

These two commands are used to add or remove a role to the list of reaction roles. Very simple to use, this makes it possible to link each role to a corresponding emoji, which will be used as a reaction for users. The emoji can be both a Discord emoji or a customized emoji of your server, even animated.

Note that it is not possible to give more than one role per emoji, and that you are limited to a certain number of roles in your server. This limit is visible via the 'list' subcommand.


-------------------
Get or leave a role
-------------------

**Syntax:** :code:`roles_react get` (alias :code:`display`)

**Syntax:** :code:`roles_react join <role>`

**Syntax:** :code:`roles_react leave <role>`

There are two ways to assign or withdraw a role: either via reaction or via a command.

For the first case, the 'get' command will display a list of available roles with their corresponding emojis, and will add each reaction at the bottom of the message. It is then sufficient to click once on a reaction to get the role, and a second time to remove it. As simple as that.

If you know exactly which role to get/remove, it is faster to use the 'join' and 'leave' subcommands followed by the role in question. You can give either the name of the role or its ID as a parameter. Note that it is not possible by this means to obtain or loose a role which is not in the list of reaction roles.


.. warning:: For the **first** command, the bot needs "`Embed Links <perms.html#embed-links>`__" and "`Add Reactions <perms.html#add-reactions>`__" permissions for this command

--------------------------
List every roles-reactions
--------------------------

**Syntax:** :code:`roles_react list`

To get a list of all the role-reactions without wasting time waiting for the bot's reactions, this command will be very useful. It also allows you to have the number of roles currently used, and the maximum number of roles you can have on your server.



-----------------
Update your embed
-----------------

**Syntax:** :code:`roles_react update <message ID> [changeDescription?] [emojis list]`

This command is very useful for those who have pinned the embed containing all the reactions of the bot. Instead of deleting and resending the message each time you add or remove a role, simply use the command to have the bot check the roles descriptions and usable reactions.

The second argument 'changeDescription' can be used when you don't want Axobot to change the embed description, and is "True" by default. If you set it to "False", it will only update the reactions (ie. adding new ones if needed).

You can also use the third argument, a list of emojis, if you want your embed to contain only specific roles/emojis. Thus you can create different roles-reactions embeds with the same system.

.. note:: Note that there are two criteria for the bot to recognize the embed as its own: it must be sent by itself, and the footer text must be the same as in the official embeds. This means that you can use the `embed` command to send a custom embed, it will still work.
