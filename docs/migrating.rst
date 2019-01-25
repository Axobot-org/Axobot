=================
Migrating from V2
=================

ZBot also allows you to retrieve information about the virtual world surrounding you. There you will find a single command that summarizes all the information about a channel/member/role/server/invitation/emoji, as well as a few other commands allowing you to study further.

New beginning, new bot, new icon, new security... Many changes have been made since the last extinction of the regretted bot fr-minecraft. Here is a non-exhaustive list of major changes:

* New name, new image, etc
* Increased safety around the token. Now it is encrypted, and hidden outside the code files
* `Server options <config.html>`_ are saved in a MySQL database, which reduces the chances of data corruption and improves option management
* This bot finally has an almost complete translation into English. A French version of the documentation is also planned
* Commands in the `Fun <fun.html>`_ section can be disabled using `server options <config.html>`_
* The `Minecraft <minecraft.html>`_ game database has grown considerably. Further improvements are expected.
* The `Slowmode <moderator.html#slowmode>`_ command no longer requires the ability to delete messages. We leave this management to Discord thanks to their new ultra-recent system.
* All userinfo, roleinfo, serverinfo (and so forth) commands have been grouped together in the `Infos <infos.html#info>`_ command
* You can now track rss flows using the `rss <rss.html>`_ command
* The `clear <moderator.html#clear>`_ control has been completely redesigned to allow more modularity while remaining very simple. Remember to check its new syntax.

To help you configure this bot, you will find a list of permissions required by the bot, as well as a list of available options.

If you need help, our `Discord server <https://discord.gg/N55zY88>`_ is open to you! And if you want to invite this bot to a server, `click here <https://discordapp.com/oauth2/authorize?client_id=486896267788812288&scope=bot&permissions=1007021171>`_!