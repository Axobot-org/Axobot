=====================
👤 User configuration
=====================

Users have a very important place in the bot code. Well, after all, without users, no bot, right? That's why we're currently working to give you as much as possible with ZBot, so you can fully enjoy your experience. 

In this section, you will find the XP module, a classic in Discord bots, as well as a command to change your own preferences, such as the color of your xp card or the language used in your personal messages. Don't worry, other possibilities are planned and will be added later!


---------
XP system
---------

The xp system is a system for evaluating a person's activity on a server using a point system. Each message brings a certain number of points to its author, allowing them to gain in levels and climb in the ranking. To avoid having a too simple system, each level is a little harder to reach than the previous one, and security measures have obviously been taken against spam or cheating.

Check the XP of someone
-----------------------

**Syntax:** :code:`rank [user]`

This command is used to view the number of xp, rank and level of a member. You can select this member either by mentioning it or by using his name or ID. If no user is given, your own XP will be displayed.

.. note:: The bot sends the format adapted to its permissions: if it can `send files <perms.html#attach-files>`__, it will display the xp card. If it can `send embeds <perms.html#embed-links>`__, it will display it in an embed, and otherwise by text.


Get the general ranking
-----------------------

**Syntax:** :code:`top [page] (guild|global)`

If you want to know who is at the top of the ranking, or who is following you so closely, this command is the ideal function. It allows you to have the name, xp and level of 20 people per page. The operation of the pages is quite intuitive: page 1 shows 20 first users, page 2 between 21 and 40, page 3 between 41 and 60, and so on. Simple, right?

If you give the argument `guild` (or `server`, as you want), the top will only display users who are on the current server, instead of all bot users.

.. note:: The bot can send this message without special permission, but don't hesitate to give him permission to `send embeds <perms.html#embed-links>`__ to make the result more aesthetic!


---------
Your info
---------

We were talking about adding customization options for each user. Here is the section that concerns them, where you can all configure some nice options to create your own identity on the bot. For the moment there are few (very few) options, but others will come later, we guarantee it!


Change your xp card
-------------------

**Syntax:** :code:`profile card [style]`

With this command, you can change the design of your xp card (the one used for the `rank` command). A long list of styles are available to everyone, but others are exclusively unlocked and reserved for certain people (more details on this part will come later).

If you use the command without argument, the bot will show you an example of a xp card with the style you currently have. But if you enter a style name that does not exist, it will give you a list of usable styles *for you*.

You can also use the command :code:`profile card-preview <style>` to get a preview of a specific style with your avatar.

.. note:: Note that to be able to display your card, the bot needs `Attach Files <perms.html#attach-files>`__ permission!


Allow or disallow an option
---------------------------

**Syntax:** :code:`profile config <option> [true|false]`

You can allow or disallow one of the configuration options via this command, much like configuring a server. Here is the list of available options


Option 'animated_card'
======================

This option allows you to enable the rendering of your xp card in.gif format if you have an animated profile image. Since the image processing time is much longer, with reduced quality, this option is disabled by default.


Option 'auto_unafk'
===================

This option has been designed for people who don't want to manually type the `unafk` command as soon as they are back. So by activating this system, Axobot will automatically remove the AFK tag from you as soon as you send a message. As simple as that!
