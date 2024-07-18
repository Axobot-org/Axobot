================
👀 Miscellaneous
================

Some commands are difficult to classify in the categories of the site. They are not used for moderation, nor to get information, they can be fun but they are not listed in this category, they don't have much to do with configuration or rss...

Here is the list of these particular commands.

----------
Bitly urls
----------

**Syntax:** :code:`bitly [create|find] <url>`

Bitly is a famous website for shortening web addresses (aka url). With this command you can create a shortcut yourself instantly using their services, and see to which address a bit.ly link refers without having to click on it. Practical, isn't it?


-----
Embed
-----

**Syntax:** :code:`embed [channel] [title] [content] [url] [footer] [image_url] [thumbnail_url] [color]`

This command is particularly useful if the 'say' command is no longer enough for you, if you want something even bigger, with colors, images and everything that goes with it. You can send embeds (these pretty boxes with colored bars), by customizing the title, content, image, title url, bar color and footer text!

Oh by the way, if you want a line break in your embed content, you can use the character :code:`\\n`, as Discord doesn't support line breaks in slash commands.

.. warning:: Hey, this may sound weird, but Axobot needs "`Embed Links <perms.html#embed-links>`__" permission to send embeds...


---------
Reminders
---------

If you have some issues with your memory like me, I think you should start using this command. With it, you can ask Axobot to remind you things to do later, between a minute and a few years. Like a `!d bump`, or anything else, up to you. And it also works in DM.

Create a new reminder
---------------------

**Syntax:** :code:`remindme <duration> <message>` or :code:`reminders create <duration> <message>`

The duration argument is exactly the same as for tempmute/tempban: use :code:`XXw` for weeks, :code:`XXd` for days, :code:`XXh` for hours and :code:`XXm` for minutes (replacing **XX** by the corresponding number, of course!)

.. warning:: Axobot needs "`Embed Links <perms.html#embed-links>`__" permission to send the reminder.

List your reminders
-------------------

**Syntax:** :code:`reminders list`

Here you will get the full list of pending reminders, waiting for the end of their timers. Nothing but a list, really.

.. note:: Giving the "`Embed Links <perms.html#embed-links>`__" permission to the bot can be useful if you want to get a better rendering.

Cancel one or more reminders
----------------------------

**Syntax:** :code:`reminders cancel [ID]`

Used when you want to stop a reminder, so Axobot will completely forget it. If you don't provide any ID, Axobot will ask you to directly select which reminders you want to cancel.

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

**Syntax:** :code:`tic-tac-toe`

Yes, we did it! A first mini-game for our bot, the tic-tac-toe! You can play against the bot in this fast and simplistic game, just by entering the command and clicking on empty cells.


----
Poll
----

**Syntax:** :code:`poll <number> [channel] [text]`

This command will add a little interactivity in your server by allowing the creation of polls. Axobot will send a message containing your text and then add reactions to it, so that members can vote.

If the specified number (the first argument) is 1, the vote will be a yes/no type. Otherwise, it will be a matter of choosing between the choices using numbers (1-20). You can also specify a channel in which the vote will be sent (by default the current channel).

If the poll text is a short message with only one line, you can directly enter it as the third argument ("text"). Otherwise, let it empty and Axobot will open a modal window to let you write your message.

For this command the bot needs "`Add Reactions <perms.html#add-reactions>`__" (add reactions to its message) and "`Use external emojis <perms.html#use-external-emojis>`" permissions.

.. note:: A big thank to the member Adri, who designed the 20 emojis used for these votes!
