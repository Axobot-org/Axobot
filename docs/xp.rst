:og:description: Track your members' activity on your server with the Axobot XP system! Gain levels, rise in the ranking, and reward your most active members with special roles!

============
🎖️ XP system
============

The XP system is a point system for evaluating a person's activity on a server. Each message earns its author a certain number of points, which can be used to gain levels and move up the rankings. In order not to make the system too easy, each level is a bit more difficult to reach than the previous one, and of course there are security measures against spam or cheating.

Configure your server
---------------------

There are several ways to customize your XP system. In particular, you have a few `configuration options <server.html#config-options>`__, each one modifying a characteristic, that you can set with the :code:`/config set <option> <value>` command or via our `online dashboard <https://axobot.xyz/dashboard>`__.

- **Enable/disable XP:** it is possible to enable or disable the entire XP system for your server via the option :code:`enable_xp`. If it is set to 'true' the system is enabled, otherwise use 'false'. By default 'false'.

- **Change the levelup message:** the bot automatically uses a long list of random messages for your members' level changes, but you can put a single one written by you via the option :code:`levelup_msg`. It is up to you to then use :code:`{user}` to mention the member, :code:`{level}` for their level and :code:`{username}` for their simple name (without notifications).

- **Select the type of XP:** there are natively three different XP systems at Axobot, modifiable with the option :code:`xp_type`: a :code:`global`, in common with all servers using this system (default), a :code:`local` respecting the same calculations but without synchronization between the servers, and a :code:`mee6-like` which uses the same rules as the famous MEE6 bot.

- **Change the gain rate of XP:** if you find that your members are not earning XP fast enough (or too fast), or if you want to make a special event XP for a limited time, you can add a gain modifier between x0.1 and x3, which will multiply by its value each point of XP earned. Not usable for the global XP system, of course. Option name: :code:`xp_rate`.

- **Move inactive members down** the leaderboard: sometimes, certain members amass a lot of XP over a period of time, then become inactive in your server, while maintaining a high ranking in the server leaderboard. One option to avoid this problem is to remove a certain amount of XP from everyone every day: inactive members will then continually lose XP. The configuration option :code:`xp_decay` lets you define the number of XP to be removed from each member every day.

- **Prevent XP in some channels:** although Axobot prevents people from earning XP with its commands, it cannot detect commands from other bots. So you can prevent your members from earning XP in certain channels via the :code:`noxp_channels` option, which contains a list of all channels where your users can't earn any experience points.

- **Prevent XP for some roles:** you can also prevent some roles from earning XP via the :code:`noxp_roles` option, which contains a list of all roles that can't earn any eXPerience points.

- **Select a channel where to send levelup messages:** sometimes levelup messages can be a bit spammy. So you have an option to select a single channel where to send level up messages. It is also possible to disable these messages via the same option. Enter the command :code:`config set levelup_channel` followed by the name of your channel, or an other special value ("none" to disable the message, "any" to select the current channel, or "dm" to send in the user's Direct Messages).

- **Silent mention in levelup messages:** when mentionning a user in a message, by default Discord sends a notification to the user. If you want to avoid this, you can set the option :code:`levelup_silent_mention` to true. The mention will then be silent, but the user will still get the red dot indicator.


Check the XP of someone
-----------------------

**Syntax:** :code:`rank [user]`

This command is used to view the XP, rank and level of a member. You can select this member by either typing in their name or ID. If no member is specified, your own XP will be displayed.

.. note:: The bot sends the format adapted to its permissions: if it can `send files <perms.html#attach-files>`__, it will display the xp card. If it can `send embeds <perms.html#embed-links>`__, it will display it in an embed, and otherwise by text.


Get the general ranking
-----------------------

**Syntax:** :code:`top [page] (global|server)`

If you want to know who is at the top of the ranking or who is following you so closely, this command is the ideal function. It allows you to see the name, XP and level of 20 people per page. Using the pages argument is quite intuitive: page 1 shows the first 20 users, page 2 between 21 and 40, page 3 between 41 and 60, and so on. Pretty straightforward, huh?

If you give the argument `server`, the top will only show users who are currently on the server, instead of all users.

.. note:: The bot will need the `send embeds <perms.html#embed-links>`__ to display the leaderboard!


Roles rewards
-------------

Roles rewards are roles given to your members when they reach a certain level of XP. These levels are defined by you (or by anyone with "Manage Server" permission), and you can add up to 10 rewards per server.

The main command to manage these roles is :code:`roles-rewards` (or its alias :code:`rr`). Here is the list of commands currently available :

* :code:`roles-rewards add <level> <role>` : allows you to add a new role to the list of roles-rewards. The level is at least 1, without maximum, and to give the role you can provide either the Identifier or the name.

* :code:`roles-rewards remove <level>` : allows you to delete a role-reward at a certain level, to prevent the next people reaching that level from getting the role. People currently with this role will not lose it, unless you perform a reload via the following command.

* :code:`roles-rewards reload` : reload all roles, to check that each member has the right roles. If a member has excess role-reward, they will be removed; similarly, if a member misses certain roles, they will be assigned to them.

* :code:`roles-rewards list` : lists all currently configured roles-rewards, with their corresponding level, as well as the maximum number of roles allowed for your server. The bot must have "`Embed Links <perms.html#embed-links>`__" permission.

.. warning:: For these roles to work properly, the bot **must** have "`Manage roles <perms.html#manage-roles>`__" permission. The roles to be given or removed **must** also be lower than the role of Axobot in your server hierarchy (Server Settings > Roles tab).
