:tocdepth: 2

======
🎳 Fun
======

This section of the bot contains lots of fun commands, which will be less useful than the other sections, but will add a good atmosphere in your server. Because a server's life is not just about moderation or utilities, Axobot couldn't be without a few moments of fun.

However, if too much fun bothers you, this option can be disabled at any time with the `config command <server.html>`__ (`enable_fun` parameter). The choice is yours!


---------------------
List of every command
---------------------

AFK
---

**Syntax:** :code:`afk [reason]` or :code:`unafk`

This command will be useful if you are often busy doing something while Discord is open. The principle is to put a tag [AFK] (which means Away From Keyboard) on you and notify anyone who tries to mention you. So there is a command to put you in AFK mode (the reason is optional, it will be indicated to people who are trying to mention you), and another command to exit AFK mode.

.. note:: Note that even if the system is specific to each server (it works with your nickname), the reason is global: if you change the reason in one server, it will be effective on all other servers having you as AFK!


Blame
-----

**Syntax:** :code:`fun blame <name>`

You've probably already gotten a chance to get mad at someone. It doesn't matter why. And since it's always better to do it together, you may like to protest collectively against a common evil. This command therefore allows you to blame someone without getting tired of spamming. You just have to enter a name and hope that its custom message exists in our database, and we'll be happy to irritate ourselves for you.

You can access even more names by being on some secret servers! Use the autocompletion to see which ones you have unlocked.

.. note:: Currently only a bunch of images exist, but if you have others to propose (that respect the theme), come see us!

.. warning:: Axobot needs "`Attach files <perms.html#attach-files>`__" permission to send its message. You're not gonna ask him to be angry without giving him permission to do it?


Bubble-wrap
-----------

**Syntax:** :code:`bubble-wrap [width=10] [height=15]` (aliases: papier-bulle, bw)

Just bubble wrap. Which pops when you squeeze it. That's all. #Just4Fun

Width should be between 1 and 150, height between 1 and 50.


Count messages
--------------

**Syntax:** :code:`fun count-messages [limit] [user] [channel]`

A nice little order that counts the number of messages in the history of this channel posted by someone. The limit corresponds to the number of messages to study in the chat, 1000 by default. And since some very old chats can have a very many many many MANY many messages (yes, 5 times *many*), we have a set limit on the number of messages you wish to search.

If no user is given as parameter, Axobot will count your own messages. Same for the channel, if you don't provide any, Axobot uses the current one.

.. warning:: It seems obvious, but the bot needs "`Read message history <perms.html#read-message-history>`__" permission to read the messages history...


Flip a coin
-----------

**Syntax:** :code:`fun flip`

Use it if you need to flip a coin, but you don't have any money to show in front of your computer's camera. Also, like real life, the piece can also fall on the edge! Isn't that great?


Kill
----

**Syntax:** :code:`fun kill [name]`

If you want to express your hatred or displeasure towards someone or something, but in a fun way, this command is for you. The bot will take a random death sentence from a long selection and insert the subject of your anger into it to create a simple and effective message. Try it at least once!


Lmgtfy
------

**Syntax:** :code:`google <search>`

Yes, that name is unpronounceable. On the other hand, commands are executed on written channels, not voice, so that's good. And, for use, refer to the website: "For all those people who find it more convenient to bother you with their question rather than search it for themselves."

.. warning:: Axobot needs "`Manage messages <perms.html#manage-messages>`__" permission to delete the invocative message.


Me
---

**Syntax:** :code:`me <text>`

When you need the bot to talk about you, like *"Z_runner runs away very fast"*, use this command.


NASA
----

**Syntax:** :code:`nasa`

If you want to see beautiful images from space, this command will suit you perfectly. It uses the official NASA API to get the Astronomy Picture of the Day, as well as a description of this image. Great for putting your head in the stars.

.. warning:: The only permission needed to grant the bot is "`Embed Links <perms.html#embed-links>`__".


HEEELP
------

**Syntax:** :code:`fun helpme`

If you need the bot to help you, type this command and see which random answer it will come out! But don't expect a miracle, it's just for fun.


Party
-----

**Syntax:** :code:`party`

Do you party often at home? If so, you have enough power to prove it with this command. And if not, she'll just put some good humor in the chat!

.. warning:: Two permissions are required for this command: "`Attach files <perms.html#attach-files>`__" and "`Use external emojis <perms.html#use-external-emojis>`__".


Pibkac
------

**Syntax:** :code:`fun pibkac`

This is a quite well-known case in IT. To quote the definition of the `Urban Dictionary <https://www.urbandictionary.com/define.php?term=pibkac>`__, *"Problem Is Between Keyboard And Chair. Another term used to refer to an id10t or other person who probably should not own a computer"*.

.. warning:: Axobot needs "`Attach files <perms.html#attach-files>`__" permission to send this gif.


Random gif
----------

**Syntax:** :code:`fun gif <cat|birthday|wink>`

This command allows you to get a random gif from a predefined list. You can choose between the following categories: `cat`, `birthday` or `wink`:
- cat: Just a random cat picture. Nothing else. But they're so cuuuuute.
- birthday: A gif to wish a happy birthday to someone, with colors and confetti!
- wink: 😉


React
-----

**Syntax:** :code:`react <messageID> <list of emojis>`

This command allows you to force the bot to add reactions to a message, which is useful in certain situations. For example, if you organize a reaction vote and want to cheat a little on the statistics!

All reactions work, whether they are Discord or server reactions. All you have to do is separate them with a space. Just like magic!

.. note:: To find out how to find the ID of a message, follow `this link <https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID->`__!

.. warning:: To find the message, Axobot must have "`Read Message History <perms.html#read-message-history>`__" permission, and "`Add Reactions <perms.html#add-reactions>`__" permission to add reactions.


Roll
----

**Syntax:** :code:`fun roll <options>`

If you can't agree with your friends, or if you want to leave the decision of a difficult choice to chance, this command will surely delight you. It allows you to select an option randomly from a list of options you provide, separated by commas (`,`). And you can put as many choices as you need!

Example: :code:`fun roll a little, a lot, passionately, madly, not at all!`


Tip
---

**Syntax:** :code:`random-tip`

If you want to get some advice on how to use the bot, or just a funny fact, you will surely find what you are looking for here. This command returns a random phrase from a defined list of "Pro-tip" and "Did you know?", to hopefully teach you something!


----------
Bot events
----------

From time to time, for special events of the year, Axobot has fun organizing an event where some small changes are made to the code. There is for example the tic-tac-toe whose symbols change, or many other small easter eggs of this kind... as well as the possibility to win event points!

To get event points, it is usually enough to use the bot: win games of tic-tac-toe, increase in xp level, or other actions of this kind.

Get info about the current event
--------------------------------

**Syntax:** :code:`events info`

You can have details about an event via this command. If an event is in progress, you will then have the explanatory summary, start and end dates, as well as any prizes to be won.

Get your current progress
-------------------------

**Syntax:** :code:`events rank`

To know your progress in the event, as well as the prices you can recover, this command is the one you need. You'll even get your ranking among all the players in the world!
