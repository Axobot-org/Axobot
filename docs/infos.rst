==============
ℹ️ Information
==============

Axobot also allows you to retrieve information about the virtual world surrounding you. There you will find a single command that summarizes all the information about a channel/member/role/server/invitation/emoji, as well as a few other commands allowing you to study further.


-----
About
-----

**Syntax:** :code:`about` or :code:`botinfo`

This command sends a short presentation text of the bot, so that you know it a little better. It will also give you some links that may be useful to you (like the one to invite the bot, or to access its Discord server).

.. note:: For this command, Axobot doesn't need any specific permission! Good news, isn't it?

----
Help
----

**Syntax:** :code:`help [command|cog]`

Allows you to know the list of all the orders currently available for you. The list is interactive, which means that you will only see the commands you are allowed to use.

You can specify a command (or subcommand) to get more details about it, or a cog (a code module) to see the list of commands related to that cog.

.. note:: For a better visual overview, it is recommended to give the permission "`Embed Links <perms.html#embed-links>`__" to the bot. In addition, you can configure the bot to `send the message as a private message <server.html#list-of-every-option>`_.

----
Info
----

**Syntax:** :code:`info [type] <object>`

This command is probably the most powerful in the information module. It allows you to find information on any item on your server: members, roles, channels, categories, emojis, invitations, as well as the server itself. Oh and also raw snowflakes (Discord IDs). Some information is even available about users who are not on your server!

You can enter the name, the mention, or the `identifier <https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID->`_ of the object to be searched, and if the type of object (member, user, role...) is not specified, the bot will search itself to identify it. Note however that you are obliged to inform the type if your search includes spaces.

.. note:: Some fields may not appear under certain conditions. No need to worry, it's just that Discord didn't send the requested information to the bot. And there's nothing we can do about it ¯\\_(ツ)_/¯

.. warning:: The necessary permissions for the bot depend on the desired result: for example "Manage webhook" is required to get the list of webhooks of a channel.

-----------
Membercount
-----------

**Syntax:** :code:`membercount`

With this command, you can get the number of members on your server, but also the number of bots, of humans, people connected, and probably other numbers that will be added later. This is a small basic command without much functionality, but it allows you to quickly keep up with these statistics.

.. note:: Good news! The bot does not need any specific permissions for this command! Just keep in mind that the rendering is much prettier with "`Embed Links <perms.html#embed-links>`__" permission enabled.

-----------
Permissions
-----------

**Syntax:** :code:`perms [channel] [user|role]` or :code:`permissions [channel] [user|role]` or :code:`permissions <integer|binary>`

This small command allows you to see the list of permissions assigned to a member/role in a particular channel. The channel can be either a text or a voice chat, but if you don't provide any, the bot will select the general permissions as set in the Server Configuration. To inform a member or a role, it is only necessary to enter his exact name, his `ID <https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID->`_ , or his mention. If no name is given the targeted member will be the one who enters the command.

As permissions are internally stored by Discord as integers or bit flags, you can also choose to view the permissions associated to a raw integer/binary value (in which case channel will be ignored). For example :code:`perms 0b01110` or :code:`perms 8` are valid syntaxes.

.. warning:: The only permission needed to grant the bot is "`Embed Links <perms.html#embed-links>`__".

----
Ping
----

**Syntax:** :code:`ping [ip adress]`

The ping command allows you to get the bot latency. It's useful if you want to check why your command takes too long to be read. The number corresponds with the delay between the moment when your message reaches Discord and the moment when the bot's response is received by the API.

If you give an ip address in the command, the bot will send a certain number of packets to this server to see if it is active, and know its latency. This may take a short time, depending on the server bandwidth and the number of packets to send.

------
Prefix
------

**Syntax:** :code:`prefix`

A nice shortcut to know the prefixes to which the bot responds. This is usually the prefix defined in the `configuration <server.html>`_, plus the mention of the bot.

..note:: You can change the bot prefix on your server with the :code:`config set prefix <new prefix>` command.


----------
Statistics
----------

**Syntax:** :code:`stats` or :code:`stats general`

An easy command to get some stats about the bot. Total XP collected by every user, number of servers using the bot, number of code lines, Python version used, and some other more or less useful facts.

**Syntax:** :code:`stats commands`

A list of the most used bot commands, sorted in descending order, both over the last 24 hours and since the beginning of the statistics recording!
