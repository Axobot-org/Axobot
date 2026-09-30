import discord

from core.bot_classes import Axobot
from core.server_warnings import (MembercounterMissingPermissions,
                                  RssDisabledFeed, RssInvalidFormat,
                                  RssMissingEmbedPermission,
                                  RssMissingTxtPermission, RssTwitterDisabled,
                                  RssUnknownChannel, RssWarning, ServerWarning,
                                  StreamNotificationMissingPermissions,
                                  StreamRoleMissingPermissions,
                                  TempRoleRemoveForbidden,
                                  TicketCreationFailed,
                                  TicketCreationUnknownTarget,
                                  TicketInitFailed,
                                  WelcomeMissingTxtPermissions,
                                  WelcomeRoleMissingPermissions)


async def build_server_warning_embed(bot: Axobot, warning: ServerWarning) -> discord.Embed | None:
    "Build the log embed of a server warning, or None if this kind of warning is unknown"
    emb = discord.Embed(colour=discord.Color.red())
    match warning:
        case WelcomeMissingTxtPermissions():
            await _welcome_missing_txt_permissions(bot, warning, emb)
        case WelcomeRoleMissingPermissions():
            _welcome_role_missing_permissions(warning, emb)
        case MembercounterMissingPermissions():
            await _membercounter_missing_permissions(bot, warning, emb)
        case RssMissingTxtPermission():
            await _rss_missing_permission(bot, warning, emb, "send_messages")
        case RssMissingEmbedPermission():
            await _rss_missing_permission(bot, warning, emb, "embed_links")
        case RssUnknownChannel():
            _rss_unknown_channel(warning, emb)
        case RssDisabledFeed():
            _rss_disabled_feed(warning, emb)
        case RssTwitterDisabled():
            _rss_twitter_disabled(warning, emb)
        case RssInvalidFormat():
            await _rss_invalid_format(bot, warning, emb)
        case TicketCreationUnknownTarget():
            _ticket_creation_unknown_target(warning, emb)
        case TicketCreationFailed():
            await _ticket_failure(bot, warning, emb, "create ticket", "manage_channels")
        case TicketInitFailed():
            await _ticket_failure(bot, warning, emb, "setup ticket permissions", "manage_permissions")
        case TempRoleRemoveForbidden():
            _temp_role_remove_forbidden(warning, emb)
        case StreamNotificationMissingPermissions():
            _stream_notification_missing_permissions(warning, emb)
        case StreamRoleMissingPermissions():
            _stream_role_missing_permissions(warning, emb)
        case _:
            return None
    return emb


async def _permissions(bot: Axobot, guild: discord.Guild, *names: str) -> str:
    "Translated names of the given permissions, one per line"
    return "\n".join([await bot._(guild.id, f"permissions.list.{name}") for name in names])


# ---- Welcomer ----

async def _welcome_missing_txt_permissions(bot: Axobot, warning: WelcomeMissingTxtPermissions, emb: discord.Embed):
    message_kind = "welcome" if warning.is_join else "leaving"
    emb.description = f"**Could not send {message_kind} message** in channel {warning.channel.mention}"
    emb.add_field(name="Missing permission", value=await _permissions(bot, warning.guild, "send_messages"))

def _welcome_role_missing_permissions(warning: WelcomeRoleMissingPermissions, emb: discord.Embed):
    emb.description = f"**Could not give welcome role** to user {warning.user.mention}"
    emb.add_field(name="Role to give", value=warning.role.mention)


# ---- Server config ----

async def _membercounter_missing_permissions(bot: Axobot, warning: MembercounterMissingPermissions, emb: discord.Embed):
    emb.description = f"**Could not update membercount channel** {warning.channel.mention}"
    permissions = await _permissions(bot, warning.guild, "read_messages", "connect", "manage_channels")
    emb.add_field(name="Required permissions", value=permissions)


# ---- RSS ----

async def _rss_missing_permission(bot: Axobot, warning: RssMissingTxtPermission | RssMissingEmbedPermission,
                                  emb: discord.Embed, permission: str):
    emb.description = f"**Could not send RSS message** in channel {warning.channel.mention}"
    emb.add_field(name="Feed ID", value=warning.feed_id)
    emb.add_field(name="Missing permission", value=await _permissions(bot, warning.guild, permission))

def _rss_unknown_channel(warning: RssUnknownChannel, emb: discord.Embed):
    emb.description = f"**Could not send RSS message** in channel {warning.channel_id}"
    _rss_reason(warning, emb, "Unknown or deleted channel")

def _rss_disabled_feed(warning: RssDisabledFeed, emb: discord.Embed):
    emb.description = f"**Feed has been disabled** in channel <#{warning.channel_id}>"
    _rss_reason(warning, emb, "Too many recent errors")

def _rss_twitter_disabled(warning: RssTwitterDisabled, emb: discord.Embed):
    emb.description = "Due to a recent Twitter API change, **Twitter feeds are not supported** anymore.\n"\
        "You should consider deleting this RSS feed."
    _rss_reason(warning, emb, "Withdrawal of the free Twitter API")

async def _rss_invalid_format(bot: Axobot, warning: RssInvalidFormat, emb: discord.Embed):
    emb.description = f"**Could not send RSS message** in channel {warning.channel.mention}"
    rss_text_cmd = await bot.get_command_mention("rss set-text")
    _rss_reason(warning, emb, f"Invalid template format. Use the {rss_text_cmd} command to fix your template.")

def _rss_reason(warning: RssWarning, emb: discord.Embed, reason: str):
    emb.add_field(name="Feed ID", value=warning.feed_id)
    emb.add_field(name="Reason", value=reason)


# ---- Tickets ----

def _ticket_creation_unknown_target(warning: TicketCreationUnknownTarget, emb: discord.Embed):
    emb.description = f"**Could not create ticket** in channel or category {warning.channel_id}"
    emb.add_field(name="Selected topic", value=warning.topic_name)
    emb.add_field(name="Reason", value="Unknown or deleted channel or category")

async def _ticket_failure(bot: Axobot, warning: TicketCreationFailed | TicketInitFailed, emb: discord.Embed,
                          action: str, permission: str):
    if isinstance(warning.channel, discord.CategoryChannel):
        where = f"category {warning.channel.name}"
    else:
        where = f"channel {warning.channel.mention}"
    emb.description = f"**Could not {action}** in {where}"
    emb.add_field(name="Selected topic", value=warning.topic_name)
    emb.add_field(name="Missing permission", value=await _permissions(bot, warning.guild, permission))


# ---- Tasks ----

def _temp_role_remove_forbidden(warning: TempRoleRemoveForbidden, emb: discord.Embed):
    emb.description = f"**Could not remove temporary role** {warning.role.mention} from user {warning.user.mention}"
    emb.add_field(name="Reason", value="Missing permission")


# ---- Twitch ----

def _stream_notification_missing_permissions(warning: StreamNotificationMissingPermissions, emb: discord.Embed):
    emb.description = f"**Could not send stream notification** in channel <#{warning.channel_id}>"
    emb.add_field(name="Streamer username", value=warning.username)

def _stream_role_missing_permissions(warning: StreamRoleMissingPermissions, emb: discord.Embed):
    emb.description = f"**Could not give stream role** to user {warning.member.mention}"
    emb.add_field(name="Streamer username", value=warning.username)
    emb.add_field(name="Role to give", value=f"<@&{warning.role_id}>")
