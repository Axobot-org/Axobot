:og:description: Axobot has a super cool streamers system allowing you to follow your favorite Twitch streamers right inside your server, and give your own streamers a special role when they're live!

=========================
🖥️ Streamers subscription
=========================

It is common for Discord communities to grow around one or a few streamers and focus their activities around these popular people. That's why Axobot offers you a simple and efficient system to follow your chosen streamers closely, and be notified when they go live.  
Moreover, if you have streamers in your community, you can assign them a special role when they are live, for example to highlight them or give them special permissions just for the time of the live!

The role you choose to give to streamers will only be given to members who have an active stream on one of the channels the server is subscribed to. Also, due to technical limitations, these streamers must have streaming activity visible on their Discord profile to receive the role (not happy with that? `Let us know <https://discord.gg/N55zY88>`__!)

.. note:: Like most of the features of this bot, this streamers subscription system is constantly being developed. Feel free to help us by offering suggestions, voting for the best ideas or reporting bugs at our `Discord server <https://discord.gg/N55zY88>`__!

.. warning:: All of these setup commands are reserved for certain roles only: you need the "Manage server" (or administrator) permission if you want to use them!


Configure your server
---------------------

**Syntax:** :code:`config set streaming_channel <channel>`

This command will set the channel where Axobot will send notifications when a streamer goes live. You can enter both the channel mention, its name, and its ID. Make sure Axobot can send messages and embeds there!

**Syntax:** :code:`config set streaming_role <role>`

This command will set the role that will be given to streamers when they go live. You can enter both the role mention, its name, and its ID. Make sure Axobot role is higher than this role and has the "Manage roles" permission!

**Syntax:** :code:`config set stream_mention <message>`

This command will set the role that will be mentioned when a streamer goes live. You can enter both the role mention, its name, and its ID. Make sure Axobot can mention it!


Subscribe or unsubscribe to a streamer
--------------------------------------

**Syntax:** :code:`twitch subscribe <channel>`

Subscribe your server to up to 20 Twitch channels with this command. You can enter both the channel name and its twitch.tv URL. Axobot will let you know if you are already subscribed to this channel or if you have reached your subscription limit

**Syntax:** :code:`twitch unsubscribe <channel>`

Unsubscribe your server from a Twitch channel. You have to enter its channel name, but slash command autocompletion will help you quickly finding it!


List your subscriptions
-----------------------

**Syntax:** :code:`twitch list-subscriptions`

This command will list all the channels your server is subscribed to, with a small notice for those that are currently live. Axobot requires the "Embed messages" permission to send the list.


Check a streamer status
-----------------------

**Syntax:** :code:`twitch check-stream <channel>`

This command will check if a streamer is currently live, and if so, will display some information about the stream. Axobot requires the "Embed messages" permission to send the message if a live is ongoing.
