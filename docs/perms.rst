===========
Permissions
===========

The permissions given to members is an important part in the configuration of a server. The same is also true for bots. This page is intended to show you each of the permissions necessary for the bot, as well as explain why they are necessary. All this in order to avoid putting unnecessary permissions on the bot, which it turn will keep your server clean and safe.

.. warning:: Never *never* **never NEVER** never *(yes, 5 times never)* put a bot with administration permissions. It has already happened once that the bot's security key is stolen, which allows the thief to take full control of the bot, such as deleting your channels or banning your members. Even though safety has been completely redesigned since this incident, zero risk is not possible. Even bots like Mee6 are not immune from carelessness.

-------------------
General Permissions
-------------------

View Audit Log
--------------

Allows the bot to read server logs (adding roles, changing names, editing channels...). Not necessary for the moment 


Manage Server
-------------

Allows the bot to change the name, image and region of the server, or get the list of all invites. Used for: `invite <infos.html#invite>`_


Manage Roles
------------

Allows the bot to create and delete roles, or edit the permissions of roles lower than his own, and to give them to other members. Used for: `mute <moderator.html#mute>`_


Manage Channels
---------------

Allows the bot to create, delete and modify channels (create invitations for example). Used for: `membercounter option <config.html#list-of-every-option>`_


Kick Members
------------

Allows the bot to eject a member from the server. Used for: `kick <moderator.html#kick>`_


Ban Members
-----------

Allows the bot to ban or unban a member from the server, as well as to consult the list of banned members. Used for: `ban <moderator.html#ban>`_ , `unban <moderator.html#id4>`_, `banlist <moderator.html#banlist>`_, `softban <moderator.html#softban>`_


Create Instant Invite
---------------------

Allows the bot to create invitations to any visible room, without being able to modify or delete them. Used for:


Change Nickname
---------------

Allows the bot to change your own nickname. Not used at this moment.


Manage Nickname
---------------

Allows the bot to change the nickname of any member hierarchically equal or inferior to you. Not used.


Manage Emojis
-------------

Allows the bot to add, rename or delete emojis from the server. Used for: `emoji <moderator.html#emoji-manager>`_


Manage Webhooks
---------------

Allows the bot to read, add, modify or delete `webhooks <https://support.discordapp.com/hc/en-us/articles/228383668-Intro-to-Webhooks>`_ . Used for: `infos <infos.html#info>`_


Read Text Channels & See Voice Channels
---------------------------------------

Allows the bot to see chats and voice channels. This permission does not allow you to write in these chats or connect to the voice channels. Required for the bot.


----------------
Text Permissions
----------------

Read Messages
-------------

Allows the bot to read messages from a chat, but not the history. In other words, the bot will react to your messages but will not be able to read them again. Remove this permission in a channel to prevent the bot from being there.


Send Messages
-------------

Allows the bot you to write messages in written rooms. Required for almost all functionalities, but not necessarily for all channels.


Send TTS Messages
-----------------

Allows the bot to send a TTS message, i.e. a message that will be read aloud by your application. No need for the bot.


Manage Messages
---------------

Allows the bot to pin or delete any message. Used for: `mute <moderator.html#mute>`_ , `freeze <moderator.html#freeze>`_ , `clear <moderator.html#clear>`_ , `purge <moderator.html#purge>`_ , `fun commands <fun.html>`_


Embed Links
-----------

Allows the bot the bot to send an embed. Used for: `membercount <infos.html#membercount>`_ , `mojang <minecraft.html#mojang>`_ . Required for: `infos <infos.html#info>`_ , `mc <minecraft.html#mc>`_ , `config see <config.html#watch>`_, `a few rss commands <rss.html>`_


Attach Files
------------

Allows the bot to send files (such as images) in a channel. Used for: `fun commands <fun.html>`_


Read Message History
--------------------

Allows the bot to read the history of all messages in a channel. Used for: `clear <moderator.html#clear>`_ , `purge <moderator.html#purge>`_ , `fun commands <fun.html>`_


Mention Everyone
----------------

Allows the bot to mention the @everyone role (which results in sending a notification to all members with access to the channel) or @here (sends a notification to all connected members with access to the channel). It is recommended to disable it.


Use External Emojis
-------------------

Allows the bot to use emojis from any other server. The bot uses them in many situations to diversify emotions, so it is strongly recommended to keep it activated.


Add Reactions
-------------

Allows the bot you to add reactions to a message, whether they are Discord or server emotions. Used for:

-----------------
Voice Permissions
-----------------

Connect
-------

Allows the bot to connect in this voice channel. It is also required to edit this channel. Used for: `membercounter option <config.html#list-of-every-option>`_

Speak
-----

Allows the bot to speak in a voice chat room. No use for the moment.