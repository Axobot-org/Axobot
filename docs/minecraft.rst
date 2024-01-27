============
🟩 Minecraft
============

At the very beginning, Axobot was a single server bot, and focused on the world-famous Minecraft game.

Even after diversifying, the bot has not forgotten its origins and remains very open to this cubic world, offering several commands related to the game. You will still find some cool commands to get information about Minecraft Java servers, player skins, or mods. There's even a command to get the status of a Minecraft Java server in real time, right into your Discord server!

--------------------------
Get a server/skin/mod info
--------------------------

**Syntax:** :code:`minecraft (server|skin|mod) <name>`

Mods info come from either the `CurseForge API <https://docs.curseforge.com>`__ or the `Modrinth API <https://docs.modrinth.com/#tag/projects>`__ (depending on which one offers the closest result to your query), so Axobot may not be able to find some mods. Please also note that their search engines sometimes behave very strangely and may not give the best results. Player and server searches use the official Mojang API and tools.

.. warning:: The bot needs the "`Embed links <perms.html#embed-links>`__" permission to send its search query, as well as "`Read message history <perms.html#read-message-history>`__" and to display the status of a server (enabled with `add` subcommand)


--------------------------
Subscribe to a server info
--------------------------

**Syntax:** :code:`minecraft follow-server <server> [port] [channel]`

This command allows you to follow a Minecraft Java server right into your channel. Axobot will post a simple embed containing some information about the server (its version, number of connected players, motd, etc.), and update it on a regular basis. You can also specify a port if the server is not running on the default port (25565), and a channel if you want to post the embed in another channel than the one where you typed the command.

.. note::
    * The bot needs the "`Embed links <perms.html#embed-links>`__" permission to send its search query, as well as "`Read message history <perms.html#read-message-history>`__" and to display the status of a server (enabled with `add` subcommand)
    * Adding server tracking automatically with `follow-server` is considered the same way as an rss feed, which means that it takes a place in your feeds list (limited to a certain number).
