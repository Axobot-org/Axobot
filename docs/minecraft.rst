============
🟩 Minecraft
============

At the very beginning, Axobot was a single server bot, and focused on the world-famous Minecraft game.

Even after diversifying, the bot has not forgotten its origins and remains very open to this cubic world, offering several commands related to the game. You will find a huge database on all the blocks, entities, items, commands, progress, potion effects, enchantments, and more. As well as a command to obtain the status of a Minecraft server (it is possible to display it permanently so that the information is refreshed regularly). And another one for the state of Mojang's servers. If you find this content is very low, don't worry: other orders are in preparation!

.. note:: The whole database comes from a single Minecraft site (French, like Axobot): `fr-minecraft.net <https://fr-minecraft.net>`__ . The search engine and the information collected are therefore those appearing on this site. If you observe any error in this database, do not hesitate to contact me so that I relay it to the administrator of the site!

.. warning:: Most of these commands are reserved for certain roles only. To allow roles to use a command, see the `config` command


---
MC
---

**Syntax:** :code:`mc <type> <name>`

This command is the main command of this module: the one that allows to search the information in the database, or to get those from a Minecraft server. To ask the bot to send the status of a server and to refresh this message regularly, use the `add` subcommand followed by the server ip. The bot will then try to edit the last message about this server, and if it can't, it will send a new one.

To search in the database, the command is disconcertingly simple: you just have to write the type of your search (entity, block, mod, etc.) followed by its name (partial or total, French or English) or its identifier (numerical or textual). The rest does itself!

To see the list of available types, enter the help mc command in the chat. If you don't find what you're looking for, don't worry: this type is probably planned for later!

Mods info come from the `CurseForge API <https://twitchappapi.docs.apiary.io/>`__ (currently managed by Twitch), so Axobot may not be able to find some mods. Please also note that their search engine is very weird, and may not have the best results. Players search use the official Mojang API, and other data come from the french `fr-minecraft.net <https://fr-minecraft.net>`__ website.

.. warning::
    * The bot needs the "`Embed links <perms.html#embed-links>`__" permission to send its search query, as well as "`Read message history <perms.html#read-message-history>`__" and to display the status of a server (enabled with `add` subcommand)
    * Adding server tracking automatically with `add` is considered the same way as an rss feed, which means that it takes a place in your feed list (limited to a certain number, except for a few special cases).


------
Mojang
------

**Syntax:** :code:`mojang` or :code:`mojang_status`

This command, much more basic, uses the Mojang API to get the status of its servers. For each server you will thus have its state, its url, as well as a short description.

.. note:: The bot does not need any specific permission for this command, however note that the appearance will look better if ""`Embed links <perms.html#embed-links>`__" permission is enabled.
