===========
Permissions
===========

The permissions given to members is an important part in the configuration of a server. The same is also true for bots. This page is intended to show you each of the permissions necessary for the bot, as well as explain why they are necessary. All this in order to avoid putting unnecessary permissions on the bot, which it turn will keep your server clean and safe.

.. warning:: Never *never* **never NEVER** never *(yes, 5 times never)* put a bot with administration permissions. It has already happened once that the bot's security key is stolen, which allows the thief to take full control of the bot, such as deleting your channels or banning your members. Even though safety has been completely redesigned since this incident, zero risk is not possible. Even bots like Mee6 are not immune from carelessness (as a MEE6 staff, I know what I'm saying).

-------------------
General Permissions
-------------------

Administrator
-------------

Grant every possible permission in the server. Someone with this permission will not have any restriction, except deleting the server and editing the roles above them. Not recommended to anyone, even a bot.


View Audit Log
--------------

Allows the bot to read server logs (adding roles, changing names, editing channels...). Not necessary for the moment 


Manage Server
-------------

Allows the bot to change the name, image and region of the server, or get the list of all invites. Used for: `invite <infos.html#invite>`__


Manage Roles
------------

Allows the bot to create and delete roles, or edit the permissions of roles lower than his own, and to give them to other members. Examples of use: `mute <moderator.html#mute-unmute>`__, `voice roles <server.html#voice-channels-managment>`__


Manage Channels
---------------

Allows the bot to create, delete and modify channels (create invitations for example). Examples of use: `membercounter option <server.html#list-of-every-option>`__, `voice channels automation <server.html#voice-channels-managment>`__


Kick Members
------------

Allows the bot to eject a member from the server. Examples of use: `kick <moderator.html#kick>`__ `anti-raid system <moderator.html#anti-raid>`__


Ban Members
-----------

Allows the bot to ban or unban a member from the server, as well as to consult the list of banned members. Examples of use: `ban <moderator.html#ban>`__ , `unban <moderator.html#id4>`__, `banlist <moderator.html#banlist>`__, `softban <moderator.html#softban>`__


Create Invite
-------------

Allows the bot to create invitations to any visible room, without being able to modify or delete them. Not used.


Change Nickname
---------------

Allows the bot to change your own nickname. Not used at this moment.


Manage Nickname
---------------

Allows the bot to change the nickname of any member hierarchically equal or inferior to you. Example of use: `unhoist command <moderator.html#unhoist-members>`__


Manage Emojis
-------------

Allows the bot to add, rename or delete emojis from the server. Example of use: `emoji <moderator.html#emoji-manager>`__


Manage Webhooks
---------------

Allows the bot to read, add, modify or delete `webhooks <https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks>`__ . Example of use: `infos <infos.html#info>`__


Read Text Channels & See Voice Channels
---------------------------------------

Allows the bot to see chats and voice channels. This permission does not allow you to write in these chats or connect to the voice channels. Required for the bot.


----------------
Text Permissions
----------------

Read Messages/See channel
-------------------------

Allows the bot to read messages from a chat, but not the history. In other words, the bot will react to your messages but will not be able to read them again. Remove this permission in a channel to prevent the bot from being there.


Send Messages
-------------

Allows the bot you to write messages in text channels. Required for almost all functionalities, but not necessarily for all channels.


Send TTS Messages
-----------------

Allows the bot to send a TTS message, i.e. a message that will be read aloud by your application. No need for the bot.


Manage Messages
---------------

Allows the bot to pin or delete any message. Examples of use: `mute <moderator.html#mute-unmute>`__ , `freeze <moderator.html#freeze>`__ , `clear <moderator.html#clear>`__ , `purge <moderator.html#purge>`__ , `fun commands <fun.html>`__


Embed Links
-----------

Allows the bot the bot to send an embed. Some commands will need that permissions, some others will only look worse. Examples of use for a better display: `membercount <infos.html#membercount>`__ , `mojang <minecraft.html#mojang>`__, `XP system <user.html#xp-system>`__ . Examples of required permission: `infos <infos.html#info>`__ , `mc <minecraft.html#mc>`__ , `config see <server.html#watch>`__, `embeds generator <miscellaneous.html#embed>`__


Attach Files
------------

Allows the bot to send files (such as images) in a channel. Examples of use: `fun commands <fun.html>`__, `XP cards <user.html#check-the-xp-of-someone>`__


Read Message History
--------------------

Allows the bot to read the history of all messages in a channel. Examples of use: `clear <moderator.html#clear>`__ , `purge <moderator.html#purge>`__ , `some fun commands <fun.html>`__


Mention @veryone, @here and @All Roles
--------------------------------------

Allows the bot to mention any role *including* @everyone (which results in sending a notification to all members with access to the channel) and @here (sends a notification to all online members with access to the channel). Zbot uses a great Discord protection to avoid unwanted mentions, so you should be safe granting it. Example of use: `rss follows with mentions <rss.html#mention-a-role>`__


Use External Emojis
-------------------

Allows the bot to use emojis from any other server. The bot uses them in many situations to diversify emotions, so it is strongly recommended to keep it activated.


Add Reactions
-------------

Allows the bot you to add reactions to a message, whether they are Discord or server emotions. Examples of use: `react <fun.html#react>`__, `vote command <miscellaneous.html#vote>`__, `poll channels <server.html#list-of-every-option>`__


-----------------
Voice Permissions
-----------------

Connect
-------

Allows the bot to connect in this voice channel. It is also required to edit this channel. Examples of use: `membercounter option <server.html#list-of-every-option>`__, `voice channels automation <server.html#voice-channels-managment>`__

Speak
-----

Allows the bot to speak in a voice chat room. No use for the moment.

Video
-----

Allows users to share their screen or their camera. Bots cannot use that for now.

Mute Members
------------

Allows users to mute other users in voice channels. Not used.

Deafen Members
--------------

Allows users to deafen other users in voice channels. Not used.

Move Members
------------

Allows the bot to move members from a voice channel to another. The bot needs to have access to that other channel, but not necessarily the affected member. Example of use: `voice channels automation <server.html#voice-channels-managment>`__

Use Voice Activity
------------------

Allows users to use voice detection instead of push-to-talk. Makes no sense for bots.

Priority Speaker
----------------

Allows users to have their volume higher than the other members in a voice channel. Bots cannot use that for now.
