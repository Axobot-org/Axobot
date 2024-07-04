:og:description: How to correctly use the mute feature and moderate your server with ease!

==============================
The mute feature: explanations
==============================

Managing the moderation of your server can sometimes be laborious or confusing. Discord offers many tools to help with moderation, but they can quickly become limited and not suitable for your specific needs.

In this article we'll look at the mute feature with Axobot, to explain how to set it up properly and use it to your advantage.


At first, what does mute mean?
==============================

Some may be confused by the use of the word "mute". When we talk about "mute" a Discord member, especially outside of a voice channel, we are talking about removing their permission to send messages. A muted member can therefore no longer send messages in your server, and in some cases can no longer join chat rooms or send feedback.

This feature was first created by third party bots, using specific roles and permissions, as we will describe next. Later, Discord decided to integrate this feature natively, calling it "time-out". This is the same system you see when you click on a member of your server with the "Time out Members" permission.

But this native tool has some limitations: it is not possible to precisely manage the permissions of a muted member, for example to allow him to speak in a specific channel (sometimes used to communicate between sanctioned members and the staff). Also, the duration selector in Discord is quite limited, offering you only a predefined choice of durations, which may not suit you.

Axobot has come up with a solution to these problems, and offers a system that will be as close as possible to your needs.


The two ways of muting with Axobot
===================================

By default, Axobot offers you to use the native Discord system to mute your members, the one called "time-out". But if you need to change the permissions of muted members, you might want to use the old mute system, through a special role.

A. The native Discord system
----------------------------

To use Discord's native time-out method, you probably won't have to activate anything. Make sure that the "muted_role" configuration option is not set to any role (:code:`/config see muted_role`), and that roles are allowed to use the :code:`/mute` command , and voila, you can start using Axobot to sanction your members!

B. The role-based system
-------------------------

If instead you prefer to be able to manage the permissions of muted members as you wish, you should create a role (conventionally called "muted") and modify your server permissions to ensure that members with this role cannot send messages.

.. tip::

    Axobot has a command to give you a first draft of this role: the :code:`/mute-config` command will create the role if no role named "muted" already exists, and then modify the permissions of your channels and categories to implement the permissions of the role.  

    This command will have two major applications, for each channel on your server: disallow posting for the "muted" role (red cross), and remove posting permission for the other specified roles (grey slash). These choices are explained further down in this text.

    As each server has its own permission rules, it is possible that the changes made by this command may not suit you, or may even break some of the systems in place. In this case you should review the Axobot modifications to correct any errors that have been introduced and make sure that everything works as expected.


Once the role is created, you can assign it as a role to be applied with the "muted_role" configuration option (the command is :code:`/config set muted_role` followed by your role).


But how should you set up your role permissions?


To begin with, it is essential to understand how permissions are applied to your members. Let's take the example of Bob, who wants to send messages in the #general channel.

- If one of Bob's roles has the "Send messages" permission in that channel, then regardless of Bob's other roles or their hierarchical position, Bob will be able to send messages in #general.
- If one of Bob's roles explicitly forbids the permission (with the red cross), and no other role allows that permission in that channel (they are all in neutral position or undefined for that channel), then Bob will not be able to send messages in #general, regardless of the other roles or the server permissions
- Finally, if none of Bob's roles influence this permission (they are all neutral or undefined), then the server permissions will apply. If one of Bob's roles allows messages to be sent globally, Bob will be able to send messages in all channels that do not specify otherwise.


This brings us to two very important rules:

1. If a role explicitly allows a permission in a channel, then that permission will be allowed for all members with that role, regardless of other roles or server permissions.
2. It is important to specify as few channel-level permissions as possible (i.e. to have as much of the neutral position, the grey slash, as possible). For example, there is no need to specify that a role can send messages in a channel if this permission is already given in the global server permissions.


Knowing this, we understand that the "muted" role can only effectively prohibit sending messages in channels if these two conditions are met:

- the muted role explicitly forbids sending messages in the channel (red cross)
- no other role explicitly allows messages to be sent in that channel (they must be in neutral position, or grey slash).

Once all these tips have been applied, and after having specified to Axobot to use this role (with the :code:`/config set muted_role` command followed by your role), you can finally use your "muted" role with peace of mind, via Axobot's :code:`/mute` command or even by manually giving it to your members!



How to actually mute someone
============================

Now that you have configured your server to use the mute feature, you can finally use it! To do so, you can use the :code:`/mute` command, which will allow you to mute a member for a specified duration, and even specify a reason for the mute.

The syntax is as follows:

.. code-block:: ini

    /mute <member> <duration> [reason]

Thus, the following commands are valid usages:

.. code-block:: ini

    /mute @Bob 1h
    /mute @Bob 1h "Spamming"
    /mute @Bob 1h 30m "Spamming"
    /mute @Bob 0 "Spamming"

The duration argument is limited to 3 years, but can support any combination of years, months, weeks, days, hours, and minutes (respectively :code:`y`, :code:`mo`, :code:`w`, :code:`d`, :code:`h`, :code:`m`).

If you want to unmute someone sooner than expected, you can use the :code:`/unmute` command, which will allow you to unmute a member before the end of the mute duration. The command simply takes the member as an argument!



Conclusion
==========

You now know how to use the mute feature of Axobot, and you can now sanction your members as you wish! If you have any questions, please do not hesitate to contact us on our support server, we will always be happy to help you!
