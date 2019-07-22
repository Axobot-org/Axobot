=============
Miscellaneous
=============

Some commands are difficult to classify in the categories of the site. They are not used for moderation, nor to get information, they can be fun but they are not listed in this category, they don't have much to do with configuration or rss... 

Here is the list of these particular commands.


-------
Camlink
-------

**Syntax:** :code:`camlink [channel]`

This command is useful for doing something that Discord has but does not yet offer to do: video calls in a server. Just connect to a voice channel on your server, then click on the link provided by the bot, and there you go! Wonderful, isn't it? With this you can share your most beautiful grins in live, or use the screen sharing for a conference, it's up to you if you want to be serious...

.. note:: As mentioned above, you must be in a voice channel of your server to use this command. Also it obviously doesn't work outside a server.

---
Say
---

**Syntax:** :code:`say [channel] <text>`

If you want to talk through the bot, as if it were sending your messages, this command will be a great help. Just indicate the text to send, and voilà, it's over. If a channel is specified, the message will be sent there. Otherwise, it will be sent in the current channel.

.. note:: Note that this command is reserved for certain roles, which you can define in the `configuration section <server.html>`_.

.. warning:: In addition, "`Manage Messages <perms.html#manage-messages>`_" permission is required if you want the bot to delete your message as soon as it has posted its copy.


----
Vote
----

**Syntax:** :code:`vote [number] <text>`

This command will add a little interactivity in your server by allowing the creation of votes or polls. Zbot will send a message containing your text and then add reactions to it, before deleting your original message.

If no number of choices is given, or if this number is 0, the vote will be a yes/no type. Otherwise, it will be a question of choosing between the choices using numbers. Note that it is not possible at this time to put more than 10 choices.

For this command the bot needs "`Add Reactions <perms.html#add-reactions>`_" (add reactions to its message), "`Read message history <perms.html#read-message-history>`_" (find its message in the chat room) and "`Manage Messages <perms.html#manage-messages>`_" (delete your message) permissions.

.. note:: A big thank to the member Adri526, for his emojis specially designed for ZBot!


-----
Embed
-----

**Syntax:** :code:`embed <args>`

This command is particularly useful if the 'say' command is no longer enough for you, if you want something even bigger, with colors, images and everything that goes with it. You can send embeds (these pretty rectangles with colored bars), by customizing the title, content, image, title url, and footer text!

Each argument is presented in the form :code:`name="value"`. If you want a line break, you can use the character :code:`\n`, and if you want to use quotation marks without closing the argument, you will have to escape them (with a \ in front). To better understand how it works, here is an example of how to use it: :code:`embed title="Here is my title!" content="Blah blah \nBlah ?" footer="Do you mean \"Text\"? "`

.. warning:: Hey, this may sound weird, but Zbot needs "`Embed Links <perms.html#embed-links>`_" permission to send embeds...


----
Crab
----

**Syntax:** :code:`crab` or :code:`morpion`

Yes, we did it! A first mini-game for our bot, the crab! You can play against the bot in this fast and simplistic game, just by entering the command and following the instructions (enter a number between 1 and 9 corresponding to the chosen cell). And the best part is that the only special permission required is to use the external emojis!


--------------
Hour & Weather
--------------

**Syntax:** :code:`hour <city>`

**Syntax:** :code:`weather <city>`

With these two commands, you can get the time (and timezone) or weather for any city in the world! All you have to do is enter the name of the city, preferably in English format (London instead of Londres for example), and the magic does the rest!

.. note:: For the `weather` command, it is better to give the "`Embed Links <perms.html#embed-links>`_" permission to the bot, to get a better rendering. But it's not mandatory!


----------
Bitly urls
----------

**Syntax:** :code:`bitly [create|find] <url>`

Bitly is a famous website for shortening web addresses (aka url). With this command you can create a shortcut yourself instantly using their services, and see to which address a bit.ly link refers without having to click on it. Practical, isn't it?