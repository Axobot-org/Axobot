===
Rss
===

More and more bots offer the feature to follow news feeds, sometimes `rss atom feeds <https://en.wikipedia.org/wiki/RSS>`_,but most often Twitter or YouTube profiles. ZBot allows you to track any rss/atom feed, as well as any Twitter/YouTube channel. For Reddit feeds, you can search for the url of the rss feed, but a command will be created to make your life easier!

With this bot you have two possibilities to follow a feed: manually request the last post, or configure an automatic follow-up in a text channel. In the case of automatic tracking, ZBot will scan all feeds every ten minutes to check for new posts, sending them in if there are any. Just be careful: this automatic tracking costs a lot of resources to the bot, so you are limited to a certain number of automatic feeds (same for rss, twitter, youtube or minecraft) !


-----------------
See the last post
-----------------

**Syntax:** :code:`rss <youtube|twitter|web> <name|link>`

This command allows you to see the last post of a youtube channel, a user on Twitter, or an rss feed. You can enter :code:`rss <type> help` to get a more complex guide to this command.

To go faster, aliases such as 'yt' or 'tw' are available! YouTube channel names or frequently used web links are already listed in the bot database. Remember to check it out!

.. note:: No specific permission is required for this command. Remember to allow the use of external emojis to get a prettier look.


-------------
Follow a feed
-------------

**Syntax:** :code:`rss add <link>`

If you want to automatically track an rss feed, this command should be used. You can only track a maximum feeds, which will be reloaded every 10 minutes. Note that Minecraft server tracing also counts as an rss feed, and therefore will cost you a place.

For Twitter and YouTube channels, simply give the link of the channel, so that the bot automatically detects the type and name of the channel. If no type is recognized, the 'web' type will be selected.

.. note:: To post a message, the bot does not need any specific permission. But if it is a Minecraft server flow (see the `corresponding section <minecraft.html>`_), don't forget the "`Read message history <perms.html#read-message-history>`_" permission!


--------------
See every feed
--------------

**Syntax:** :code:`rss list`

If you want to keep an eye on the number of rss/Minecraft feeds registered on your server, this is the command to use. The bot will search in the depths of its incomprehensible files to bring back the list of all the flows, and summarize them for you in a nice embed.

.. warning:: The bot needs "`Embed Links <perms.html#embed-links>`_" permission!


--------------
Mention a role
--------------

**Syntax:** :code:`rss roles [flow ID]`

This rss flow tracking option allows you to notify a role when a new post arrives. The roles mentioned are different between rss flows, which allows you a greater handling. 

The "flow ID" argument is the identifier of the flow (found with the command `rss list<#see-every-feed>`_). If you do not enter this argument, or if the feed can't be found, the bot will open a menu where you can choose which feed to modify. Then another menu will allow you to choose which roles you want to mention.

.. warning:: For this command too, the bot needs "`Embed Links <perms.html#embed-links>`_" permission!


----------------------
Delete a followed feed
----------------------

**Syntax:** :code:`rss remove [flow ID]`

With this command, you can stop following an rss/minecraft flow. And it's also very easy to use. Just one command and *poof*, we shut down the machinery.

The "flow ID" argument is the identifier of the flow (found with the command `rss list<#see-every-feed>`_). If you do not enter this argument, or if the feed can't be found, the bot will open a menu where you can choose which feed to modify.

.. warning:: ZBot needs "`Embed Links <perms.html#embed-links>`_" permission to send the selection list!


-----------------
Reload every feed
-----------------

**Syntax:** :code:`rss reload`

If your favorite youtube channel has just posted a new cool video, and the bot takes too long to post it in your specially designed living room, you can force it to refresh the list of your youtube, twitter and other websites, in addition to Minecraft servers. This command will allow you in a few seconds to be again at the top of the latest news!

.. note:: Note that to avoid lags, a 10-minute cooldown is active on this command.