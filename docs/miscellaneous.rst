================
👀 Miscellaneous
================

Some commands are difficult to classify in the categories of the site. They are not used for moderation, nor to get information, they can be fun but they are not listed in this category, they don't have much to do with configuration or rss...

Here is the list of these particular commands.

------
Admins
------

**Syntax:** :code:`admins`

If you want to quickly know who are the Axobot administrators. Easy to use, quick to read, always up-to-date.

----------
Bitly urls
----------

**Syntax:** :code:`bitly [create|find] <url>`

Bitly is a famous website for shortening web addresses (aka url). With this command you can create a shortcut yourself instantly using their services, and see to which address a bit.ly link refers without having to click on it. Practical, isn't it?


----
Book
----

This command allows you to manage your own library, saving your books easily. You can also only use the search function, for example to share a specific book with your Discord friends. Anything is possible!


.. warning:: This command is under construction, and is therefore only in its early stages. Feel free to give your ideas on the official `bot server <https://discord.gg/N55zY88>`__!

Search by ISBN
--------------

**Syntax:** :code:`book search <ISBN>`

Used to search for a book from its ISBN, and displays its main information. ISBNs of length 10 and 13 are accepted.


----------
Changelogs
----------

**Syntax:** :code:`changelogs [version]` or :code:`changelogs list`

If you want to know the bot modification log, what has been changed in the last version or an older one, you can use this command. Introduced in version 3.5.5, it allows access to all bot changelogs from this version. For older versions, you will have to go directly to the channels of the official server!

.. note:: Giving the "`Embed Links <perms.html#embed-links>`__" permission to the bot can be useful if you want to get a better rendering. But it's not mandatory!


-----
Embed
-----

**Syntax:** :code:`embed <args>`

This command is particularly useful if the 'say' command is no longer enough for you, if you want something even bigger, with colors, images and everything that goes with it. You can send embeds (these pretty rectangles with colored bars), by customizing the title, content, image, title url, color and footer text!

Each argument is presented in the form :code:`name="value"`. If you want a line break, you can use the character :code:`\\n`, and if you want to use quotation marks without closing the argument, you will have to escape them (with a \ in front). To better understand how it works, here is an example of how to use it: :code:`embed title="Here is my title!" content="Blah blah \\nBlah ?" footer="Do you mean \\"Text\\"? "`

.. warning:: Hey, this may sound weird, but Axobot needs "`Embed Links <perms.html#embed-links>`__" permission to send embeds...


--------------
Hour & Weather
--------------

**Syntax:** :code:`hour <city>`

**Syntax:** :code:`weather <city>`

With these two commands, you can get the time (and timezone) or weather for any city in the world! All you have to do is enter the name of the city, preferably in English format (London instead of Londres for example), and the magic does the rest!

.. note:: For the `weather` command, it is better to give the "`Embed Links <perms.html#embed-links>`__" permission to the bot, to get a better rendering. But it's not mandatory!


--------
Markdown
--------

**Syntax:** :code:`markdown`

The markdown is a set of formatting rules used everywhere, such as on GitHub or Discord. This command gives you these formatting rules, which will allow you to display spoilers, code blocks, or just simple strikethrough or italicized text.

.. warning:: Warning, this command contains an invitation link to the information server on the code blocks.


------------------------
Python formatting (pep8)
------------------------

**Syntax:** :code:`pep8 <code>`

Python's formatting conventions can sometimes be difficult to remember. Summaries exist on the internet, but there are several hundred rules, all more or less specific to their use cases. That's why Axobot offers you to automatically format your Python code following the "PEP 8" (PEP for Python Extension Proposal) rules with a simple command.


---------
Reminders
---------

If you have some issues with your memory like me, I think you should start using this command. With it, you can ask Axobot to remind you things to do later, between a minute and a few years. Like a `!d bump`, or anything else, up to you. And it also works in DM.

Create a new reminder
---------------------

**Syntax:** :code:`remindme <duration> <message>` or :code:`reminder create <duration> <message>`

The duration argument is exactly the same as for tempmute/tempban: use :code:`XXw` for weeks, :code:`XXd` for days, :code:`XXh` for hours and :code:`XXm` for minutes (replacing **XX** by the corresponding number, of course!)

.. warning:: Axobot needs "`Embed Links <perms.html#embed-links>`__" permission to send the reminder.

List your reminders
-------------------

**Syntax:** :code:`reminder list`

Here you will get the full list of pending reminders, waiting for the end of their timers. Nothing but a list, really.

.. note:: Giving the "`Embed Links <perms.html#embed-links>`__" permission to the bot can be useful if you want to get a better rendering.

Delete one or more reminders
----------------------------

**Syntax:** :code:`reminder delete [ID]`

Used when you want to stop a reminder, so Axobot will completely forget it. If you don't provide any ID, Axobot will ask you to directly select which reminders you want to delete.

Clear every reminders
---------------------

**Syntax:** :code:`reminders clear`

If you have too many pending reminders and want to cancel them all, instead of deleting them one by one you can just use that command. For you own sake, the bot will ask you to confirm your choice by a simple reaction to click.


---
Say
---

**Syntax:** :code:`say [channel] <text>`

If you want to talk through the bot, as if it were sending your messages, this command will be a great help. Just indicate the text to send, and voilà, it's over. If a channel is specified, the message will be sent there. Otherwise, it will be sent in the current channel.

.. note:: Note that this command is reserved for certain roles, which you can define in the `configuration section <server.html>`__.

.. warning:: In addition, "`Manage Messages <perms.html#manage-messages>`__" permission is required if you want the bot to delete your message as soon as it has posted its copy.


-----------
Tic-tac-toe
-----------

**Syntax:** :code:`tic-tac-toe` (alias :code:`morpion`) or :code:`tic-tac-toe leave`

Yes, we did it! A first mini-game for our bot, the crab! You can play against the bot in this fast and simplistic game, just by entering the command and following the instructions (enter a number between 1 and 9 corresponding to the chosen cell). And the best part is that the only special permission required is to use the external emojis!

By using the *leave* argument you can instantly stop a game. This can be useful if you are stuck by a bug and can't join a game for example.

.. note:: If you want to disable the game in your server, or only to reduce the amount of messages sent, you can edit your "ttt_display" `config option <server.html#list-of-every-option>`__


----
Vote
----

**Syntax:** :code:`vote [number] <text>`

This command will add a little interactivity in your server by allowing the creation of votes or polls. Axobot will send a message containing your text and then add reactions to it, before deleting your original message.

If no number of choices is given, or if this number is 0, the vote will be a yes/no type. Otherwise, it will be a question of choosing between the choices using numbers. Note that it is not possible at this time to put more than 10 choices.

For this command the bot needs "`Add Reactions <perms.html#add-reactions>`__" (add reactions to its message), "`Read message history <perms.html#read-message-history>`__" (find its message in the chat room) and "`Manage Messages <perms.html#manage-messages>`__" (delete your message) permissions.

.. note:: A big thank to the member Adri, for his emojis specially designed for Axobot!
