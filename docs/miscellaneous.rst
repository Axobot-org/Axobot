=============
Miscellaneous
=============

Some commands are difficult to classify in the categories of the site. They are not used for moderation, nor to get information, they can be fun but they are not listed in this category, they don't have much to do with configuration or rss... 

Here is the list of these particular commands.


---
Say
---

**Syntax:** :code:`say [channel] <text>`

If you want to talk through the bot, as if it were sending your messages, this command will be a great help. Just indicate the text to send, and voilà, it's over. If a channel is specified, the message will be sent there. Otherwise, it will be sent in the current channel.

.. note:: Note that this command is reserved for certain roles, which you can define in the `configuration section <config.html>`_.

.. warning:: In addition, "`Manage Messages <perms.html#manage-messages>`_" permission is required if you want the bot to delete your message as soon as it has posted its copy.


----
Vote
----

**Syntax:** :code:`vote [number] <text>`

This command will add a little interactivity in your server by allowing the creation of votes or polls. Zbot will send a message containing your text and then add reactions to it, before deleting your original message.

If no number of choices is given, or if this number is 0, the vote will be a yes/no type. Otherwise, it will be a question of choosing between the choices using numbers. Note that it is not possible at this time to put more than 10 choices.

For this command the bot needs "`Add Reactions <perms.html#add-reactions>`_" (add reactions to its message), "`Read message history <perms.html#read-message-history>`_" (find its message in the chat room) and "`Manage Messages <perms.html#manage-messages>`_" (delete your message) permissions.

.. note:: A big thank to the member Adri526, for his emojis specially designed for ZBot!