==================
User configuration
==================

Users have a very important place in the bot code. Well, after all, without users, no bot, right? That's why we're currently working to give you as much as possible with ZBot, so you can fully enjoy your experience. 

In this section, you will find the XP module, a classic in Discord bots, as well as a command to change your own preferences, such as the color of your xp card or the language used in your personal messages. Don't worry, other possibilities are planned and will be added later!


---------
XP system
---------

The xp system is a system for evaluating a person's activity on a server using a point system. Each message brings a certain number of points to its author, allowing him to gain in levels and climb in the ranking. To avoid having a too simple system, each level is a little harder to reach than the previous one, and security measures have obviously been taken against spam or cheating.

Check the XP of someone
-----------------------

**Syntax:** :code:`rank [user]`

This command is used to view the number of xp, rank and level of a member. You can select this member either by mentioning it or by using his name or ID. If no user is given, your own XP will be displayed.

.. note:: The bot sends the format adapted to its permissions: if it can `send files <perms.html#attach-files>`_, it will display the xp card. If it can `send embeds <perms.html#embed-links>`_, it will display it in an embed, and otherwise by text.


Get the general ranking
-----------------------

**Syntax:** :code:`top [page]`

If you want to know who is at the top of the ranking, or who is following you so closely, this command is the ideal function. It allows you to have the name, xp and level of 20 people per page. The operation of the pages is quite intuitive: page 1 shows 20 first users, page 2 between 21 and 40, page 3 between 41 and 60, and so on. Simple, right?

.. note:: The bot can send this message without special permission, but don't hesitate to give him permission to `send embeds <perms.html#embed-links>`_ to make the result more aesthetic!