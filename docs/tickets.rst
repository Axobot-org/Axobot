:og:description: Axobot has a nice fresh tickets system, allowing your members to contact the staff in an easy and private way, without having to resort to DMs or role mentions.

=================
❓ Tickets system
=================

A popular feature for very active servers is the ability for their members to quickly contact their staff when needed, without disturbing the moderators at any time of the day or night.

Axobot offers this very intuitive system, letting users open a "ticket" when they need it, and creating a private channel for them that only staff roles can read. This allows both your members to be sure to keep their information private, your teams to not be bothered by unsolicited mentions or DMs, and you to see at a glance which tickets are currently active and quickly respond.

.. note:: Like most of the features of this bot, this tickets system is constantly being developed. Feel free to help us by offering suggestions, voting for the best ideas or reporting bugs at our `Discord server <https://discord.gg/N55zY88>`__!

.. warning:: All of these setup commands are reserved for certain roles only: you need the "Manage channels" (or administrator) permission if you want to use them!


----------
How to use
----------

As staff: Send the prompt message
---------------------------------

**Syntax:** :code:`tickets portal summon [channel]`

Once you have configured the necessary (see the following chapters), you should display the prompt so that your members can select a topic and open their ticket. Using this command will ask Axobot to send a message containing the presentation message and the topic selector.

We recommend using this command in a info channel, or pinning the result, so that it is easily accessible by your members. Please note that only members with the **permission to "manage channels"** can use it.


As a user: open a new ticket
----------------------------

Opening a new ticket through Axobot's system is very intuitive, and you will be guided through the whole process.

It all starts with selecting a topic with the selector sent by Axobot. Try to choose the most suitable topic for your request, and if none is suitable, you can always choose the "Other" topic.

Once you have chosen a topic, Axobot may send you a help message related to your topic. Make sure you read it carefully, as it is intended to help you as much as possible and avoid you having to open a ticket for nothing. If this help is useful to you, or if you still want to open a ticket, just click on the corresponding button.

Then a popup will ask you to choose a name for your ticket. Be sure to choose a meaningful name that expresses your issue in a few words. You are limited to 100 characters, so keep it straightforward. Submitting this short form will validate your ticket and create a channel just for you.

Depending on the server configuration, Axobot will either open a new channel in a category or a thread in a given channel. If it has sufficient permissions, only you, Axobot and the server staff will be allowed to read and talk in your ticket, to respect your privacy. Once your request is resolved, ask the staff in question to close the channel.


----------------
Setup the basics
----------------

Presentation message
--------------------

**Syntax:** :code:`tickets portal set-text <message>`:

This message will be sent just above the topic selector, to introduce your members to the feature. You can write whatever you want, as long as it doesn't exceed 2000 characters.


Tickets category/channel
------------------------

**Syntax:** :code:`tickets portal set-category <category>` or :code:`tickets portal set-channel <channel>`:

When a member wants to open a ticket, Axobot will create a channel just for them in your server. You need to tell it which category to create the ticket channels in, and make sure it has permission to "Manage Roles" and "Manage Channels".

If you have the new feature of private threads, you may also want to use them instead of channels, to avoid having to create a large number of channels in your server. Just specify a channel instead of the category, and make sure Axobot has permission to create private threads there.


Default staff role
------------------

**Syntax:** :code:`tickets portal set-role <role or "none">`

You can choose who will have access to the ticket channels (besides the concerned member, Axobot and the server administrators) with this command. The role given as a parameter will automatically be given the permissions to read tickets and moderate messages. If you don't want to allow a particular role, use the command with the word "none".

.. note:: You can define a specific staff role for each ticket topic. The next chapter explains how.


Default hint
------------

**Syntax:** :code:`tickets portal set-hint <message or "none">`

If you wish, Axobot can send a short help message when a member wants to create a ticket, to try to solve their problem before the ticket is created. The user will then have the choice to find this message useful and abandon the process, or to continue and open their ticket.

It is usually desirable to customize this message according to the ticket topic chosen by the user. The next chapter will show you how to do this.

Default channel name format
---------------------------

**Syntax:** :code:`tickets portal set-format <format or "none">`

At first Axobot will automatically choose the channel name when someones open a new ticket, based on the user nickname and tag. But you can wish for more customized names, and want to compose your own name format based on the available placeholders listed below:
* `username`: the user name (like "Z_runner")
* `userid`: the internal user ID, which is usually a 18-digits number unique to this user
* `topic`: the topic name selected by the user
* `topic_emoji`: the emoji of the topic selected by the user
* `ticket_name`: the name or subject provided by the user during the ticket creation

Please note that Discord channel names are limited to 100 characters and do not allow spaces or non-ascii characters.

You can also use the "none" keyword to reset the format to its default value.

Create a new topic
------------------

**Syntax:** :code:`tickets topic add [emote] <name>`

When opening a ticket, your members have the possibility to choose between several different topics. This allows your staff to get general information about the opened ticket, to choose different roles associated with each type of ticket, as well as to customize the information displayed to your members (for example the help message).

To create a new topic, use the command above. You can optionally choose an emoji to be displayed next to the topic name in the selector.


Delete a topic
--------------

**Syntax:** :code:`tickets topic remove`

To delete a topic in a simple way, use the command above. Axobot will ask you which topic to delete, you just have to select the right one from the list and the bot will take care of everything!


Review your config
------------------

**Syntax:** :code:`tickets review-config`

Once you're done configuring Axobot, you can use this command to review your configuration and make sure everything is correct. Axobot will send you a message containing all the information you need to know about your configuration.

When using slash commands, you can also select a specific topic to review its configuration in more depth.


-------------------
Customize per topic
-------------------

Edit a topic emoji
------------------

**Syntax:** :code:`tickets topic set-emote [topic ID] <emote or "none">`

Edit or delete the emote associated with a particular topic. If you don't enter a topic ID, Axobot will ask you directly which topic to edit via an intuitive menu. Use the keyword "none" to delete the emoji associated with the topic.


Edit a topic name
-----------------

**Syntax:** :code:`tickets topic set-name [topic ID] <name>`

Edit the name of a topic. If you don't enter a topic ID, Axobot will ask you directly which topic to edit via an intuitive menu. The name must be less than 100 characters long.


Topic-specific hint
-------------------

**Syntax:** :code:`tickets topic set-hint [topic ID] <message or "none">`

Edit the help message associated with a topic. The help message will be displayed after a user selects this topic, offering the user to abandon the procedure if the help has been sufficiently effective. If you don't enter a topic ID, Axobot will ask you directly which topic to edit via an intuitive menu.

Use the "none" keyword to use the default help message (see previous chapter), or to skip this step if no default message has been configured.


Topic-specific staff role
-------------------------

**Syntax:** :code:`tickets topic set-role [topic ID] <role or "none">`

Edit the role allowed to read tickets related to this particular topic. Users with the role passed in parameter will be able to read all tickets opened with this topic, reply to them, and close them. If you don't enter a topic ID, Axobot will ask you directly which topic to edit via an intuitive menu.

Use the "none" keyword to use the default staff role (see previous chapter), or no role at all (outside of admins) if no default role has been configured.


Topic-specific channel name format
----------------------------------

**Syntax:** :code:`tickets topic set-format [topic ID] <format or "none">`

Same than for the default channel name format, but specific to the given topic. Use the "none" keyword to use the server default format.
