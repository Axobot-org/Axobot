:og:description: Discover every Discord permission Axobot can use, what each one is needed for, and which ones you can safely leave out.
:tocdepth: 2

==============
🔓 Permissions
==============

The permissions given to members are an important part of a server's configuration. The same is true for bots. This page shows each permission the bot may need, and explains why it is needed. The goal is to avoid granting unnecessary permissions to the bot, which keeps your server clean and safe.

.. warning:: Never *never* **never NEVER** never *(yes, 5 times never)* put a bot with administration permissions. It has already happened once that the bot's security token was stolen, which allowed the thief to take full control of the bot, such as deleting channels or banning members. Even though security has been completely redesigned since this incident, zero risk is not possible. See `this official note from Discord <https://discord.com/moderation/1500000176222-201-permissions-on-discord#title-2>`__ for more information.


-------------------
General Permissions
-------------------

Administrator
-------------

Grants every possible permission in the server. Someone with this permission has no restriction, except deleting the server and editing the roles above them. Not recommended for anyone, even a bot.

View Audit Log
--------------

Allows the bot to read server logs (adding roles, changing names, editing channels...). Examples of use: `server logs <moderator.html#server-logs>`__

Manage Server
-------------

Allows the bot to change the name, image and region of the server, or get the list of all invites. Used by: `invite tracking <invites-tracking.html>`__

Manage Roles
------------

Allows the bot to create and delete roles, or edit roles lower than its own, and to give them to other members. Examples of use: `mute <moderator.html#mute-unmute>`__, `voice roles <server.html#voice-channels-managment>`__, `tickets <tickets.html>`__

Manage Channels
---------------

Allows the bot to create, delete and modify channels (create invitations for example). Examples of use: `membercounter option <server.html#list-of-every-option>`__, `voice channels automation <server.html#voice-channels-managment>`__, `slowmode <moderator.html#slowmode>`__, `tickets <tickets.html>`__

Kick, Approve and Reject Members
--------------------------------

Allows the bot to kick a member from the server, and to approve or reject join requests for servers with whitelists. Examples of use: `kick <moderator.html#kick>`__, `anti-raid system <moderator.html#anti-raid>`__

Ban Members
-----------

Allows the bot to ban or unban a member from the server, as well as to view the list of banned members. Examples of use: `ban <moderator.html#ban>`__ , `unban <moderator.html#id4>`__, `banlist <moderator.html#banlist>`__, `softban <moderator.html#softban>`__

Time out Members
----------------

Allows the bot to temporarily mute a member, preventing them from sending messages, adding reactions, and speaking in voice channels. Examples of use: `mute <moderator.html#mute-unmute>`__

Create Invite
-------------

Allows the bot to create invitations to any visible channel, without being able to modify or delete them. Not used.

Change Nickname
---------------

Allows the bot to change its own nickname. Not used at this moment.

Manage Nicknames
----------------

Allows the bot to change the nickname of any member whose highest role is lower than the bot's. Example of use: `unhoist command <moderator.html#unhoist-members>`__

Create Expressions
------------------

Allows the bot to add custom emojis, stickers and sounds to the server. Example of use: `emoji <moderator.html#emoji-manager>`__

Manage Expressions
------------------

Allows the bot to edit or remove emojis, stickers and sounds from the server. Example of use: `emoji <moderator.html#emoji-manager>`__

View Server Insights
--------------------

Lets members view the server insights (community growth, engagement...). Not usable by bots.

View Server Subscription Insights
---------------------------------

Lets members view the server subscription insights (revenue, subscribers, free trials). Not usable by bots.

Manage Webhooks
---------------

Allows the bot to read, add, modify or delete `webhooks <https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks>`__ . Example of use: `info <infos.html#info>`__

Read Text Channels & See Voice Channels
---------------------------------------

Legacy name of `View Channels`_ in the text permissions below. Allows the bot to see text and voice channels, without allowing it to write in them or connect to them. Required for the bot.

Create Events
-------------

Allows the bot to create server events. Not used by Axobot.

Manage Events
-------------

Allows the bot to edit and cancel server events. Not used by Axobot.


----------------
Text Permissions
----------------

View Channels
-------------

Allows the bot to see a channel and read its new messages, but not its history. Remove this permission in a channel to prevent the bot from seeing it.

Send Messages and Create Posts / Send Messages in Threads and Posts
-------------------------------------------------------------------

Allows the bot to write messages in text channels, threads, and forum posts. Required for almost all functionalities, but not necessarily for all channels.

Create Public/Private Threads
-----------------------------

Allows the bot to create public or private threads in text channels. Required for the `tickets system <tickets.html>`__ when configured to create threads.

Send Text-to-speech Messages
----------------------------

Allows the bot to send a TTS (text-to-speech) message, i.e. a message that will be read aloud to everyone focused on the channel. Not needed by Axobot.

Embed Links
-----------

Allows the bot to send embeds. Some commands need this permission, while others will only look worse without it. Examples of better display: `membercount <infos.html#membercount>`__ , `mojang <minecraft.html#mojang>`__, `XP system <xp.html>`__ . Examples of required permission: `info <infos.html#info>`__ , `minecraft <minecraft.html#mc>`__ , `config see <server.html#watch>`__, `embeds generator <miscellaneous.html#embed>`__

Attach Files
------------

Allows the bot to send files (such as images) in a channel. Examples of use: `fun commands <fun.html>`__, `XP cards <xp.html#check-the-xp-of-someone>`__

Read Message History
--------------------

Allows the bot to read the history of all messages in a channel. Examples of use: `clear <moderator.html#clear>`__ , `purge <moderator.html#purge>`__ , `some fun commands <fun.html>`__

Mention @everyone, @here and All Roles
--------------------------------------

Allows the bot to mention any role *including* @everyone (which results in sending a notification to all members with access to the channel) and @here (sends a notification to all online members with access to the channel). Axobot uses Discord's allowed-mentions protection to avoid unwanted mentions, so it should be safe to grant. Example of use: `rss follows with mentions <rss.html#mention-a-role>`__

Use External Emojis
-------------------

Allows the bot to use emojis from any other server. The bot uses them in many situations to express more emotions, so it is strongly recommended to keep it enabled.

Use External Stickers
---------------------

Lets members use stickers from other servers. Bots cannot send stickers, so this permission has no effect on them.

Manage Messages
---------------

Allows the bot to delete any message or remove its embeds. Examples of use: `mute <moderator.html#mute-unmute>`__ , `freeze <moderator.html#freeze>`__ , `clear <moderator.html#clear>`__ , `purge <moderator.html#purge>`__ , `fun commands <fun.html>`__

Pin Messages
------------

Allows the bot to pin or unpin any message. Example of use: `tickets <tickets.html>`__ (the first message of a ticket is pinned).

Bypass Slowmode
---------------

Allows the bot to send messages without being affected by slowmode. Not needed.

Manage Threads and Posts
------------------------

Allows the bot to rename, delete, close and set slowmode on threads and posts, and to view private threads. Not used at this moment.

Send Voice Messages
-------------------

Allows the bot to send voice messages. Not used by Axobot.

Create Polls
------------

Allows the bot to create native Discord polls. Not used by the bot, whose poll system relies on reactions.

Add Reactions
-------------

Allows the bot to add reactions to a message, whether they are Discord or server emojis. Examples of use: `react <fun.html#react>`__, `poll command <miscellaneous.html#poll>`__, `poll channels <server.html#list-of-every-option>`__

Use Application Commands
------------------------

Allows members to use bot commands (i.e. slash commands as well as user and message context commands). Required for Axobot's commands to be usable.

Use Activities
--------------

Lets members use Activities. Not usable by bots.

Use External Apps
-----------------

Lets apps added to a member's account post messages publicly; when disabled, their responses are private. Not usable by bots.


-----------------
Voice Permissions
-----------------

Connect
-------

Allows the bot to connect to a voice channel. It is also required to edit that channel. Examples of use: `membercounter option <server.html#list-of-every-option>`__, `voice channels automation <server.html#voice-channels-managment>`__

Speak
-----

Allows the bot to speak in a voice channel. Not used at this moment.

Video
-----

Lets members share their screen or camera. Not usable by bots.

Use Soundboard
--------------

Allows members to play sounds from the server soundboard. Not used by Axobot.

Use External Sounds
-------------------

Allows members to use soundboard sounds from other servers. Not used by Axobot.

Set Voice Channel Status
------------------------

Allows members to create and edit voice channel statuses. Not used by Axobot.

Mute Members
------------

Allows members to mute other members in voice channels. Not used.

Deafen Members
--------------

Allows members to deafen other members in voice channels. Not used.

Move Members
------------

Allows the bot to move members from one voice channel to another. The bot needs access to the destination channel, but the affected member does not. Example of use: `voice channels automation <server.html#voice-channels-managment>`__

Use Voice Activity
------------------

Lets members speak using voice detection instead of push-to-talk. Not usable by bots.

Priority Speaker
----------------

Lets members be heard louder than others in a voice channel. Not usable by bots.

Request To Speak
----------------

Lets members raise their hand in `stage channels <https://support.discord.com/hc/en-us/articles/1500005513722-Stage-Channels-FAQ>`__. Not usable by bots.
