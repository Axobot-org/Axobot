:og:description: Axobot's invitation tracking system lets you know which invitation is used when a new member joins your server! Read this page to find out how to get the most out of it.

===================
🔍 Invites tracking
===================

Axobot's invites tracking system allows you to track which invitation is being used when a new member joins your server. This feature is especially useful to know where your members are coming from and how effective your invitations are.

.. note::
    This feature requires the "Manage server" permission to be enabled for Axobot. Else, Axobot cannot read your invitation list and will not be able to track their usage.


Enable/Disable the invite tracking
----------------------------------

**Syntax:** :code:`invites-tracking enable` or :code:`invites-tracking disable`

This is how you can start or stop tracking the usage of your server invitations. If enabled, Axobot will automatically save the current state of your invitations, and compare it with the new state when a new member joins your server. If the member has been invited by someone, Axobot will tell you which invitation was used in the corresponding `moderation log <moderator.html#server-logs>`__.

These commands have the same effect as using the `/config set <server.html#modify>`__ command with the "enable_invites_tracking" option.


Get informed with your server logs
----------------------------------

When a new member joins your server, Axobot will automatically check which invitation was used to invite them. If the invite tracking is enabled, Axobot will add a new field to the "member_join" `moderation log <moderator.html#server-logs>`__ to inform you which invitation was used and who created it.

To enable this moderation log in a channel, use the :code:`/modlogs enable member_join` command.


Attach a custom name to an invitation
-------------------------------------

**Syntax:** :code:`invites-tracking set-name <invite> <name>`

This command allows you to attach a custom name to an invitation so that you can easily identify it in the logs. The name can be up to 60 characters long, including spaces and special characters. Whether you specify a custom name or not, Axobot will always display the invitation code in the logs.

If you want to remove the custom name attached to an invitation, use the special keyword :code:`none` as the name.


Review your invitations usage
-----------------------------

**Syntax:** :code:`invites-tracking list-invites`

This command lists all invitations created on your server, along with the number of times they have been used and the date they were created. If you have attached a custom name to an invitation, it will be displayed next to the invitation code.

Note: the built-in Discord page found in your server settings will not display the custom names attached to your invitations, but will contain more info than this command (notably the maximum number of uses and the expiration date).


Resynchronize your invitations tracking
----------------------------------------

**Syntax:** :code:`invites-tracking resync`

If you ever find out that Axobot is not tracking your invitations correctly, you can use this command to force Axobot to resynchronize your invitations. This will update the list of invitations saved by Axobot and ensure they are up to date with the current state of your server.
