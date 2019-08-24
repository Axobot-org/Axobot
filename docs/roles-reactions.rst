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

**Syntax:** :code:`roles_react get`

**Syntax:** :code:`roles_react get <role>` (alias :code:`join`)

**Syntax:** :code:`roles_react leave <role>`

There are two ways to assign or withdraw a role: either via reaction or via a command.

For the first case, the 'get' command alone will display a list of available roles with their corresponding emojis, and will add each reaction at the bottom of the message. It is then sufficient to click once on a reaction to get the role, and a second time to remove it. As simple as that.

If you know exactly which role to get/remove, it is faster to use the 'get' and 'leave' subcommands followed by the role in question. You can give either the name of the role or its ID as a parameter. Note that it is not possible by this means to obtain a role which is not in the list of reaction roles.


.. warning:: For the **first** command, the bot needs "`Embed Links <perms.html#embed-links>`_" and "`Add Reactions <perms.html#add-reactions>`_" permissions for this command

--------------------------
List every roles-reactions
--------------------------

**Syntax:** :code:`roles_react list`

To get a list of all the role-reactions without wasting time waiting for the bot's reactions, this command will be very useful. It also allows you to have the number of roles currently used, and the maximum number of roles you can have on your server.