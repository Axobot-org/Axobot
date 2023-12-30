import json
import logging
from typing import Literal, Optional, TypedDict, Union

import discord
from discord.app_commands import locale_str as _T
from discord.ext import commands

from libs.arguments.args import UnicodeEmoji
from libs.bot_classes import Axobot, MyContext
from libs.emojis_manager import EmojisManager
from libs.getch_methods import getch_channel_or_thread
from libs.serverconfig.options_list import options as options_list

log = logging.getLogger("runner")
UnicodeEmojis = EmojisManager(None).unicode_set

class IntOptionRepresentation(TypedDict):
    "Configuration for an integer option"
    type: Literal["int"]
    min: int
    max: int
    default: Optional[int]
    is_listed: bool

class FloatOptionRepresentation(TypedDict):
    "Configuration for a float option"
    type: Literal["float"]
    min: float
    max: Optional[float]
    default: Optional[float]
    is_listed: bool

class BooleanOptionRepresentation(TypedDict):
    "Configuration for a boolean option"
    type: Literal["boolean"]
    default: Optional[bool]
    is_listed: Optional[bool]

class EnumOptionRepresentation(TypedDict):
    "Configuration for an enum option"
    type: Literal["enum"]
    values: tuple[str]
    default: Optional[str]
    is_listed: bool

class TextOptionRepresentation(TypedDict):
    "Configuration for a text (string) option"
    type: Literal["text"]
    min_length: int
    max_length: int
    default: Optional[str]
    is_listed: bool

class RoleOptionRepresentation(TypedDict):
    "Configuration for a discord role option"
    type: Literal["role"]
    allow_integrated_roles: bool
    allow_everyone: bool
    default: None
    is_listed: bool

class RolesListOptionRepresentation(TypedDict):
    "Configuration for a list of discord roles option"
    type: Literal["roles_list"]
    min_count: int
    max_count: int
    allow_integrated_roles: bool
    allow_everyone: bool
    default: None
    is_listed: bool

class TextChannelOptionRepresentation(TypedDict):
    "Configuration for a discord text channel option"
    type: Literal["text_channel"]
    allow_threads: bool
    allow_announcement_channels: bool
    allow_non_nsfw_channels: bool
    default: None
    is_listed: bool

class TextChannelsListOptionRepresentation(TypedDict):
    "Configuration for a list of discord text channels option"
    type: Literal["text_channels_list"]
    min_count: int
    max_count: int
    allow_threads: bool
    allow_announcement_channels: bool
    allow_non_nsfw_channels: bool
    default: None
    is_listed: bool

class VoiceChannelOptionRepresentation(TypedDict):
    "Configuration for a discord voice channel option"
    type: Literal["voice_channel"]
    allow_stage_channels: bool
    allow_non_nsfw_channels: bool
    default: None
    is_listed: bool

class CategoryOptionRepresentation(TypedDict):
    "Configuration for a discord category option"
    type: Literal["category"]
    default: None
    is_listed: bool

class EmojisListOptionRepresentation(TypedDict):
    "Configuration for a list of emojis option (both Unicode and discord emojis)"
    type: Literal["emojis_list"]
    min_count: int
    max_count: int
    default: Optional[list[str]]
    is_listed: bool

class ColorOptionRepresentation(TypedDict):
    "Configuration for a color option (stored as an int)"
    type: Literal["color"]
    default: Optional[int]
    is_listed: bool

class LevelupChannelOptionRepresentation(TypedDict):
    "Configuration for a levelup channel option"
    type: Literal["levelup_channel"]
    default: Optional[str]
    is_listed: bool

AllRepresentation = Union[
    IntOptionRepresentation,
    FloatOptionRepresentation,
    BooleanOptionRepresentation,
    EnumOptionRepresentation,
    TextOptionRepresentation,
    RoleOptionRepresentation,
    RolesListOptionRepresentation,
    TextChannelOptionRepresentation,
    TextChannelsListOptionRepresentation,
    VoiceChannelOptionRepresentation,
    CategoryOptionRepresentation,
    EmojisListOptionRepresentation,
    ColorOptionRepresentation,
    LevelupChannelOptionRepresentation,
]

class OptionConverter:
    "Base class for option converters"
    @staticmethod
    async def from_raw(raw: str, representation: TypedDict, guild: discord.Guild):
        raise NotImplementedError

    @staticmethod
    def to_raw(value) -> str:
        raise NotImplementedError

    @staticmethod
    def to_display(option_name: str, value) -> str:
        raise NotImplementedError

    @staticmethod
    async def from_input(raw: str, representation: TypedDict, guild: discord.Guild, ctx: MyContext):
        raise NotImplementedError

def get_converter(option_name: str):
    "Get the correct converter to use for a given config option"
    if data := options_list.get(option_name):
        data_type = data["type"]
        if data_type == "int":
            return IntOption
        if data_type == "float":
            return FloatOption
        if data_type == "boolean":
            return BooleanOption
        if data_type == "enum":
            return EnumOption
        if data_type == "text":
            return TextOption
        if data_type == "role":
            return RoleOption
        if data_type == "roles_list":
            return RolesListOption
        if data_type == "text_channel":
            return TextChannelOption
        if data_type == "text_channels_list":
            return TextChannelsListOption
        if data_type == "voice_channel":
            return VoiceChannelOption
        if data_type == "category":
            return CategoryOption
        if data_type == "emojis_list":
            return EmojisListOption
        if data_type == "color":
            return ColorOption
        if data_type == "levelup_channel":
            return LevelupChannelOption
        raise ValueError(f"Invalid option type: {data_type}")
    raise ValueError(f"Invalid option name: {option_name}")

async def from_raw(option_name: str, raw: str, guild: discord.Guild):
    "Convert an option value to a usable object"
    if raw is None:
        return None
    converter = get_converter(option_name)
    return await converter.from_raw(raw, options_list[option_name], guild)

def to_raw(option_name: str, value):
    "Convert a config object to a string value, for storage in db"
    if value is None:
        return None
    converter = get_converter(option_name)
    return converter.to_raw(value)

async def to_display(option_name: str, value, guild: discord.Guild, bot: "Axobot") -> Optional[str]:
    "Convert a config object to a string value, for display in embeds"
    if value is None:
        if option_name == "levelup_msg":
            return "default"
        return None
    converter = get_converter(option_name)
    result = converter.to_display(option_name, value)
    if isinstance(result, discord.app_commands.locale_str):
        return await bot._(guild, result.message)
    return result

async def from_input(option_name: str, raw: str, guild: discord.Guild, ctx: MyContext):
    "Convert a user input to a config object"
    if raw is None:
        return None
    converter = get_converter(option_name)
    return await converter.from_input(raw, options_list[option_name], guild, ctx)

class IntOption(OptionConverter):
    "Option converter for integer values"
    @staticmethod
    async def from_raw(raw: str, representation: IntOptionRepresentation, guild: discord.Guild):
        try:
            value = int(raw)
            if value < representation["min"]:
                value = representation["min"]
            elif representation["max"] is not None and value > representation["max"]:
                value = representation["max"]
            return value
        except ValueError:
            raise ValueError("Invalid int value") from None

    @staticmethod
    def to_raw(value: int):
        return str(value)

    @staticmethod
    def to_display(_option_name, value: int):
        return str(value)

    @staticmethod
    async def from_input(raw: str, representation: IntOptionRepresentation, guild: discord.Guild, ctx: MyContext):
        try:
            value = int(raw)
        except ValueError:
            raise ValueError("Invalid int value", "INT_INVALID", representation) from None
        if value < representation["min"]:
            raise ValueError("Value is too low", "INT_TOO_LOW", representation)
        if representation["max"] is not None and value > representation["max"]:
            raise ValueError("Value is too high", "INT_TOO_HIGH", representation)
        return value

class FloatOption(OptionConverter):
    "Option converter for float values"
    @staticmethod
    async def from_raw(raw: str, representation: FloatOptionRepresentation, guild: discord.Guild):
        try:
            value = float(raw)
            if value < representation["min"]:
                value = representation["min"]
            elif representation["max"] is not None and value > representation["max"]:
                value = representation["max"]
            return value
        except ValueError:
            raise ValueError("Invalid positive int value") from None

    @staticmethod
    def to_raw(value: float):
        return str(value)

    @staticmethod
    def to_display(_option_name, value: float):
        return str(value)

    @staticmethod
    async def from_input(raw: str, representation: FloatOptionRepresentation, guild: discord.Guild, ctx: MyContext):
        try:
            value = round(float(raw), 3)
        except ValueError:
            raise ValueError("Invalid float value", "FLOAT_INVALID", representation) from None
        if value < representation["min"]:
            raise ValueError("Value is too low", "FLOAT_TOO_LOW", representation)
        elif representation["max"] is not None and value > representation["max"]:
            raise ValueError("Value is too high", "FLOAT_TOO_HIGH", representation)
        return value

class BooleanOption(OptionConverter):
    "Option converter for boolean values"
    @staticmethod
    async def from_raw(raw: str, representation: BooleanOptionRepresentation, guild: discord.Guild):
        return raw.lower() == "true"

    @staticmethod
    def to_raw(value: bool):
        return str(value)

    @staticmethod
    def to_display(_option_name, value: bool):
        if value:
            return _T("server.bool.true")
        else:
            return _T("server.bool.false")

    @staticmethod
    async def from_input(raw: str, representation: BooleanOptionRepresentation, guild: discord.Guild, ctx: MyContext):
        true_ish = {"1", "true", "yes", "on", "oui"}
        false_ish = {"0", "false", "no", "off", "non"}
        if raw.lower() not in true_ish | false_ish:
            raise ValueError("Invalid boolean value", "BOOLEAN_INVALID", representation)
        return raw.lower() in true_ish

class EnumOption(OptionConverter):
    "Option converter for enum values"
    @staticmethod
    async def from_raw(raw: str, representation: EnumOptionRepresentation, guild: discord.Guild):
        if raw == "(╯°□°）╯︵ ┻━┻":
            return "extreme"
        if raw not in representation["values"]:
            raise ValueError("Invalid enum value")
        return raw

    @staticmethod
    def to_raw(value: str):
        return value

    @staticmethod
    def to_display(option_name, value: str):
        return _T(f"server.enum.{option_name}.{value}")

    @staticmethod
    async def from_input(raw: str, representation: EnumOptionRepresentation, guild: discord.Guild, ctx: MyContext):
        if raw.lower() not in representation["values"]:
            raise ValueError("Invalid enum value", "ENUM_INVALID", representation)
        return raw.lower()

class TextOption(OptionConverter):
    "Option converter for text (string) values"
    @staticmethod
    async def from_raw(raw: str, representation: TextOptionRepresentation, guild: discord.Guild):
        return raw

    @staticmethod
    def to_raw(value: str):
        return value

    @staticmethod
    def to_display(_option_name, value: str):
        return value

    @staticmethod
    async def from_input(raw: str, representation: TextOptionRepresentation, guild: discord.Guild, ctx: MyContext):
        if len(raw) < representation["min_length"]:
            raise ValueError("Text is too short", "TEXT_TOO_SHORT", representation)
        elif len(raw) > representation["max_length"]:
            raise ValueError("Text is too long", "TEXT_TOO_LONG", representation)
        return raw

class RoleOption(OptionConverter):
    "Option converter for discord role values"
    @staticmethod
    async def from_raw(raw: str, representation: RoleOptionRepresentation, guild: discord.Guild):
        try:
            role_id = int(raw)
        except ValueError:
            log.warning("[RoleConverter] Invalid role id: %s", raw)
            return None
        role = guild.get_role(role_id)
        if role is None:
            log.warning("[RoleConverter] Role not found: %s", raw)
            return None
        return role

    @staticmethod
    def to_raw(value: discord.Role):
        return str(value.id)

    @staticmethod
    def to_display(_option_name, value: discord.Role):
        return value.mention

    @staticmethod
    async def from_input(raw: str, representation: RoleOptionRepresentation, guild: discord.Guild, ctx: MyContext):
        try:
            role = await commands.RoleConverter().convert(ctx, raw)
        except commands.BadArgument:
            if raw == "everyone":
                role = guild.default_role
            else:
                raise ValueError("Invalid role", "ROLE_INVALID", representation, raw) from None
        if not representation["allow_integrated_roles"] and role.is_integration():
            raise ValueError("Integrated roles are not allowed", "ROLE_INTEGRATED", representation)
        if not representation["allow_everyone"] and role.is_default():
            raise ValueError("Everyone role is not allowed", "ROLE_EVERYONE", representation)
        return role

class RolesListOption(OptionConverter):
    "Option converter for a list of discord role values"
    @staticmethod
    async def from_raw(raw: str, representation: RolesListOptionRepresentation, guild: discord.Guild) -> list[discord.Role]:
        role_ids = json.loads(raw)
        if any(not isinstance(id, int) for id in role_ids):
            log.warning("[RolesListConverter] Invalid role ids: %s", role_ids)
            role_ids = [id for id in role_ids if isinstance(id, int)]
        roles = [guild.get_role(id) for id in role_ids]
        if None in roles:
            log.warning("[RolesListConverter] Some roles not found: %s", role_ids)
            roles = [role for role in roles if role is not None]
        return roles

    @staticmethod
    def to_raw(value: list[discord.Role]):
        return json.dumps([role.id for role in value])

    @staticmethod
    def to_display(_option_name, value: list[discord.Role]):
        return ", ".join(role.mention for role in value)

    @staticmethod
    async def from_input(raw: str, representation: RolesListOptionRepresentation, guild: discord.Guild, ctx: MyContext):
        roles: list[discord.Role] = []
        for word in raw.split(" "):
            try:
                role = await commands.RoleConverter().convert(ctx, word)
            except commands.BadArgument:
                if word == "everyone":
                    role = guild.default_role
                else:
                    raise ValueError("Invalid role", "ROLE_INVALID", representation, word) from None
            if not representation["allow_integrated_roles"] and role.is_integration():
                raise ValueError("Integrated roles are not allowed", "ROLE_INTEGRATED", representation)
            if not representation["allow_everyone"] and role.is_default():
                raise ValueError("Everyone role is not allowed", "ROLE_EVERYONE", representation)
            if role in roles:
                continue
            roles.append(role)
        if len(roles) < representation["min_count"]:
            raise ValueError("Too few roles", "ROLES_TOO_FEW", representation)
        elif len(roles) > representation["max_count"]:
            raise ValueError("Too many roles", "ROLES_TOO_MANY", representation)
        return roles

class TextChannelOption(OptionConverter):
    "Option converter for discord text channel values"
    @staticmethod
    async def from_raw(raw: str, representation: TextChannelOptionRepresentation, guild: discord.Guild):
        try:
            channel_id = int(raw)
        except ValueError:
            log.warning("[TextChannelConverter] Invalid channel id: %s", raw)
            return None
        channel = await getch_channel_or_thread(guild, channel_id)
        if channel is None:
            log.warning("[TextChannelConverter] Channel not found: %s", raw)
            return None
        return channel

    @staticmethod
    def to_raw(value: Union[discord.TextChannel, discord.Thread]):
        return str(value.id)

    @staticmethod
    def to_display(_option_name, value: Union[discord.TextChannel, discord.Thread]):
        return value.mention

    @staticmethod
    async def from_input(raw: str, representation: TextChannelOptionRepresentation, guild: discord.Guild, ctx: MyContext):
        try:
            channel = await commands.GuildChannelConverter().convert(ctx, raw)
        except commands.BadArgument:
            raise ValueError("Invalid channel", "CHANNEL_INVALID", representation, raw) from None
        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            raise ValueError("Channel is not a text channel", "CHANNEL_NOT_TEXT", representation)
        if (not representation["allow_threads"]) and isinstance(channel, discord.Thread):
            raise ValueError("Threads are not allowed", "CHANNEL_THREAD", representation)
        if (not representation["allow_announcement_channels"]) and channel.is_news():
            raise ValueError("Announcement channels are not allowed", "CHANNEL_ANNOUNCEMENT", representation)
        if not (representation["allow_non_nsfw_channels"] or channel.is_nsfw()):
            raise ValueError("Non-NSFW channels are not allowed", "CHANNEL_NON_NSFW", representation)
        return channel

class TextChannelsListOption(OptionConverter):
    "Option converter for a list of discord text channel values"
    @staticmethod
    async def from_raw(raw: str, representation: TextChannelsListOptionRepresentation, guild: discord.Guild
                       ) -> list[Union[discord.TextChannel, discord.Thread]]:
        channel_ids = json.loads(raw)
        if any(not isinstance(id, int) for id in channel_ids):
            log.warning("[TextChannelsListConverter] Invalid channel ids: %s", channel_ids)
            channel_ids = [id for id in channel_ids if isinstance(id, int)]
        channels: list[Union[discord.TextChannel, discord.Thread]] = []
        for channel_id in channel_ids:
            if channel := await getch_channel_or_thread(guild, channel_id):
                channels.append(channel)
            else:
                log.warning("[TextChannelsListConverter] Channel not found: %s", channel_id)
        if None in channels:
            log.warning("[TextChannelsListConverter] Some channels not found: %s", channel_ids)
            channels = [channel for channel in channels if channel is not None]
        return channels

    @staticmethod
    def to_raw(value: list[Union[discord.TextChannel, discord.Thread]]):
        return json.dumps([channel.id for channel in value])

    @staticmethod
    def to_display(_option_name, value: list[Union[discord.TextChannel, discord.Thread]]):
        return ", ".join(channel.mention for channel in value)

    @staticmethod
    async def from_input(raw: str, representation: TextChannelsListOptionRepresentation, guild: discord.Guild, ctx: MyContext):
        channels: list[Union[discord.TextChannel, discord.Thread]] = []
        for word in raw.split(" "):
            try:
                channel = await commands.GuildChannelConverter().convert(ctx, word)
            except commands.BadArgument:
                raise ValueError("Invalid channel", "CHANNEL_INVALID", representation, word) from None
            if not isinstance(channel, (discord.TextChannel, discord.Thread)):
                raise ValueError("Channel is not a text channel", "CHANNEL_NOT_TEXT", representation)
            if (not representation["allow_threads"]) and isinstance(channel, discord.Thread):
                raise ValueError("Threads are not allowed", "CHANNEL_THREAD", representation)
            if (not representation["allow_announcement_channels"]) and channel.is_news():
                raise ValueError("Announcement channels are not allowed", "CHANNEL_ANNOUNCEMENT", representation)
            if not (representation["allow_non_nsfw_channels"] or channel.is_nsfw()):
                raise ValueError("Non-NSFW channels are not allowed", "CHANNEL_NON_NSFW", representation)
            if channel in channels:
                continue
            channels.append(channel)
        if len(channels) < representation["min_count"]:
            raise ValueError("Too few channels", "CHANNELS_TOO_FEW", representation)
        elif len(channels) > representation["max_count"]:
            raise ValueError("Too many channels", "CHANNELS_TOO_MANY", representation)
        return channels

class VoiceChannelOption(OptionConverter):
    "Option converter for discord voice channel values"
    @staticmethod
    async def from_raw(raw: str, representation: VoiceChannelOptionRepresentation, guild: discord.Guild):
        try:
            channel_id = int(raw)
        except ValueError:
            log.warning("[VoiceChannelConverter] Invalid channel id: %s", raw)
            return None
        channel = await getch_channel_or_thread(guild, channel_id)
        if not isinstance(channel, discord.channel.VocalGuildChannel):
            log.warning("[VoiceChannelConverter] Channel not found: %s", raw)
            return None
        return channel

    @staticmethod
    def to_raw(value: discord.channel.VocalGuildChannel):
        return str(value.id)

    @staticmethod
    def to_display(_option_name, value: discord.channel.VocalGuildChannel):
        return value.mention

    @staticmethod
    async def from_input(raw: str, representation: VoiceChannelOptionRepresentation, guild: discord.Guild, ctx: MyContext):
        try:
            channel = await commands.GuildChannelConverter().convert(ctx, raw)
        except commands.BadArgument:
            raise ValueError("Invalid channel", "CHANNEL_INVALID", representation, raw) from None
        if not isinstance(channel, discord.channel.VocalGuildChannel):
            raise ValueError("Channel is not a voice channel", "CHANNEL_NOT_VOICE", representation)
        if not representation["allow_stage_channels"] and isinstance(channel, discord.StageChannel):
            raise ValueError("Stage channels are not allowed", "CHANNEL_STAGE", representation)
        if not representation["allow_non_nsfw_channels"] and not channel.is_nsfw():
            raise ValueError("Non-NSFW channels are not allowed", "CHANNEL_NON_NSFW", representation)
        return channel

class CategoryOption(OptionConverter):
    "Option converter for discord category values"
    @staticmethod
    async def from_raw(raw: str, representation: CategoryOptionRepresentation, guild: discord.Guild):
        try:
            channel_id = int(raw)
        except ValueError:
            log.warning("[CategoryConverter] Invalid category id: %s", raw)
            return None
        channel = await getch_channel_or_thread(guild, channel_id)
        if not isinstance(channel, discord.CategoryChannel):
            log.warning("[CategoryConverter] Category not found: %s", raw)
            return None
        return channel

    @staticmethod
    def to_raw(value: discord.CategoryChannel):
        return str(value.id)

    @staticmethod
    def to_display(_option_name, value: discord.CategoryChannel):
        return value.name

    @staticmethod
    async def from_input(raw: str, representation: CategoryOptionRepresentation, guild: discord.Guild, ctx: MyContext):
        try:
            channel = await commands.CategoryChannelConverter().convert(ctx, raw)
        except commands.BadArgument:
            raise ValueError("Invalid category", "CATEGORY_INVALID", representation) from None
        return channel

class EmojisListOption(OptionConverter):
    "Option converter for a list of emojis (both Unicode and discord emojis)"
    @staticmethod
    async def from_raw(raw: str, representation: EmojisListOptionRepresentation, guild: discord.Guild):
        emoji_ids: list[Union[str, int]] = json.loads(raw)
        if any(not isinstance(id, (int, str)) for id in emoji_ids):
            log.warning("[EmojisListConverter] Invalid emoji ids: %s", emoji_ids)
            emoji_ids = [id for id in emoji_ids if isinstance(id, (int, str))]
        emojis: list[Union[UnicodeEmoji, discord.Emoji]] = []
        for emoji_id in emoji_ids:
            if isinstance(emoji_id, int):
                guild_emojis = [emoji for emoji in guild.emojis if emoji.id == emoji_id]
                if guild_emojis:
                    emojis.append(guild_emojis[0])
                else:
                    log.warning("[EmojisListConverter] Emoji not found: %s", emoji_id)
                    continue
            elif all(char in UnicodeEmojis for char in emoji_id):
                emojis.append(emoji_id)
            else:
                log.warning("[EmojisListConverter] Invalid emoji: %s", emoji_id)
        return emojis

    @staticmethod
    def to_raw(value: list[Union[UnicodeEmoji, discord.Emoji]]):
        return json.dumps([emoji.id if isinstance(emoji, discord.Emoji) else emoji for emoji in value])

    @staticmethod
    def to_display(_option_name, value: list[Union[UnicodeEmoji, discord.Emoji]]):
        return " ".join(str(emoji) for emoji in value)

    @staticmethod
    async def from_input(raw: str, representation: EmojisListOptionRepresentation, guild: discord.Guild, ctx: MyContext):
        emojis: list[Union[UnicodeEmoji, discord.Emoji]] = []
        for emoji in raw.split():
            if emoji in UnicodeEmojis:
                if emoji in emojis:
                    continue
                emojis.append(UnicodeEmoji(emoji))
            else:
                try:
                    emoji = await commands.EmojiConverter().convert(ctx, emoji)
                except commands.BadArgument:
                    raise ValueError("Invalid emoji", "EMOJI_INVALID", representation) from None
                if emoji not in guild.emojis:
                    raise ValueError("Invalid emoji", "EMOJI_INVALID", representation)
                if emoji in emojis:
                    continue
                emojis.append(emoji)
        if len(emojis) < representation["min_count"]:
            raise ValueError("Too few emojis", "EMOJIS_TOO_FEW", representation)
        elif len(emojis) > representation["max_count"]:
            raise ValueError("Too many emojis", "EMOJIS_TOO_MANY", representation)
        return emojis

class ColorOption(OptionConverter):
    "Option converter for color values"
    @staticmethod
    async def from_raw(raw: str, representation: ColorOptionRepresentation, guild: discord.Guild):
        try:
            color = int(raw, 16)
        except ValueError:
            raise ValueError("Invalid color") from None
        if color < 0 or color > 0xFFFFFF:
            raise ValueError("Invalid color")
        return color

    @staticmethod
    def to_raw(value: int):
        return f"{value:06X}"

    @staticmethod
    def to_display(_option_name, value: int):
        return f"#{value:06X}"

    @staticmethod
    async def from_input(raw: str, representation: ColorOptionRepresentation, guild: discord.Guild, ctx: MyContext):
        try:
            color = await commands.ColorConverter().convert(ctx, raw)
        except commands.BadArgument:
            raise ValueError("Invalid color", "COLOR_INVALID", representation) from None
        return int(color)

class LevelupChannelOption(OptionConverter):
    "Option converter for levelup channel values"
    @staticmethod
    async def from_raw(raw: str, representation: LevelupChannelOptionRepresentation, guild: discord.guild):
        if raw in {"any", "none", "dm"}:
            return raw
        channel_repr: TextChannelOptionRepresentation = representation | {
            "allow_threads": True,
            "allow_announcement_channels": True,
            "allow_non_nsfw_channels": True,
        }
        return await TextChannelOption.from_raw(raw, channel_repr, guild)

    @staticmethod
    def to_raw(value: Union[str, discord.TextChannel]):
        if isinstance(value, str):
            return value
        return TextChannelOption.to_raw(value)

    @staticmethod
    def to_display(option_name, value: Union[str, discord.TextChannel]):
        if isinstance(value, str):
            return _T(f"server.enum.{option_name}.{value}")
        return TextChannelOption.to_display(option_name, value)

    @staticmethod
    async def from_input(raw: str, representation: LevelupChannelOptionRepresentation, guild: discord.Guild, ctx: MyContext):
        if raw.lower() in {"any", "none", "dm"}:
            return raw.lower()
        channel_repr: TextChannelOptionRepresentation = representation | {
            "allow_threads": True,
            "allow_announcement_channels": True,
            "allow_non_nsfw_channels": True,
        }
        try:
            return await TextChannelOption.from_input(raw, channel_repr, guild, ctx)
        except ValueError:
            raise ValueError("Invalid levelup channel option", "LEVELUP_CHANNEL_INVALID", representation) from None
