===
Rss
===

More and more bots offer the feature to follow news feeds, sometimes `rss atom feeds <https://en.wikipedia.org/wiki/RSS>`_,but most often Twitter or YouTube profiles. ZBot allows you to track any rss/atom feed, as well as any Twitter/YouTube/Twitch/DeviantArt channel. For Reddit feeds, you can search for the url of the rss feed, but a command will be created to make your life easier!

With this bot you have two possibilities to follow a feed: manually request the last post, or configure an automatic follow-up in a text channel. In the case of automatic tracking, ZBot will scan all feeds every ten minutes to check for new posts, sending them in if there are any. Just be careful: this automatic tracking costs a lot of resources to the bot, so you are limited to a certain number of automatic feeds (same for rss, twitter, youtube or minecraft) !

To manage this plugin (add, edit or remove feeds), you will need at least the Manage Server permission.

-----------------
See the last post
-----------------

**Syntax:** :code:`rss <youtube|twitter|twitch|deviant|web> <name|link>`

This command allows you to see the last post of a youtube channel, a user on Twitter or Twitch or DeviantArt, or an rss feed. You can enter :code:`rss <type> help` to get a more complex guide to this command.

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

**Syntax:** :code:`rss roles [flow ID] [roles]`

This rss flow tracking option allows you to notify a role when a new post arrives. The roles mentioned are different between rss flows, which allows you a greater handling. 

The "flow ID" argument is the identifier of the flow (found with the command `rss list <#see-every-feed>`_). If you do not enter this argument, or if the feed can't be found, the bot will open a menu where you can choose which feed to modify. Then another menu will allow you to choose which roles you want to mention.

The "roles" arguments is the list of roles you want to mention, separated by spaces (if some of them contains spaces, you can use quotations "..." instead). If not specified, Zbot will ask you for the list. You can either use names or IDs, or put "none" to remove every mention.

.. warning:: For this command too, the bot needs "`Embed Links <perms.html#embed-links>`_" permission!


---------------
Change the text
---------------

**Syntax:** :code:`rss text [flow ID] [new text]`

This command is particularly useful if you want to change the text of an rss flow tracking, for example to have a customized text, or in your native language. Many tools are at your disposal (also known as *variables*) that allow an optimal personalization of the message. That's right, we thought of you.

If the rss feed ID is not given, the bot will open a menu to select it. And for the text, if you have forgotten it, the bot will also ask you to know it, and will provide you the current text and a list of the usable variables.

.. note:: Available variables are:

    - :code:`{author}`: the author of the post
    - :code:`{channel}`: the channel name (usually the same as author)
    - :code:`{date}`: the post date (UTC)
    - :code:`{link}` or :code:`{url}`: a link to the post
    - :code:`{logo}`: an emoji representing the type of post (web, Twitter, YouTube...)
    - :code:`{mentions}`: the list of mentioned roles
    
    - {title}: the title of the post

.. warning:: Yo know what? For this command, the bot needs "`Embed Links <perms.html#embed-links>`_" permission!


-----------
Move a feed
-----------

**Syntax:** :code:`rss move [flow ID] [new channel]`

If you want to move an rss feed without having to delete it, recreate a new one and then reconfigure it, you can use this command. It can also be useful to configure a flow in a secret chat room, then reveal it to your entire server without having to temporarily close your chat!

If no identifier is given, the bot will ask you which one to modify.  As for the channel, if you do not specify any, it will select the one in which you type the command.

.. warning:: Here again, the bot needs "`Embed Links <perms.html#embed-links>`_" permission!


------------------
Setup a feed embed
------------------

**Syntax:** :code:`rss use_embed [flow ID] [use embed]` or :code:`rss embed <flow ID> [use embed] <parameters>`

Sometimes people want to have a lot of control over what is happening in the world. Since we are unable to offer it to them, we offer you a great control on the embeds sent by rss flows. The first command allows you to enable the use of embed instead of classic text, the second one allows you to choose a title, a color and a custom footer.

For the first command, if you do not give the feed identifier or a boolean value, the bot will ask you for it. However, you must give it yourself for the second command (you can find it via the `rss list <#see-every-feed>`_ command).

The syntax of the color/text customization parameters is the same as for the `embed <miscellaneous.html#embed>`_ command, i.e. in the form :code:`key = "value"`, with the possible keys "color", "footer" and "title".



----------------------
Delete a followed feed
----------------------

**Syntax:** :code:`rss remove [flow ID]`

With this command, you can stop following an rss/minecraft flow. And it's also very easy to use. Just one command and *poof*, we shut down the machinery.

The "flow ID" argument is the identifier of the flow (found with the command `rss list <#see-every-feed>`_). If you do not enter this argument, or if the feed can't be found, the bot will open a menu where you can choose which feed to modify.

.. warning:: ZBot needs "`Embed Links <perms.html#embed-links>`_" permission to send the selection list!


-----------------
Reload every feed
-----------------

**Syntax:** :code:`rss reload`

If your favorite youtube channel has just posted a new cool video, and the bot takes too long to post it in your specially designed living room, you can force it to refresh the list of your youtube, twitter and other websites, in addition to Minecraft servers. This command will allow you in a few seconds to be again at the top of the latest news!

.. note:: Note that to avoid lags, a 10-minute cooldown is active on this command.
