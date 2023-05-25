from typing import Union

import discord
from discord import Interaction
from discord.app_commands import Choice
from discord.app_commands import locale_str as _T

from libs.bot_classes import Axobot
from libs.serverconfig.converters import (BooleanOptionRepresentation,
                                          CategoryOptionRepresentation,
                                          EmojisListOptionRepresentation,
                                          EnumOptionRepresentation,
                                          FloatOptionRepresentation,
                                          IntOptionRepresentation,
                                          LevelupChannelOptionRepresentation,
                                          RoleOptionRepresentation,
                                          TextChannelOptionRepresentation,
                                          TextOptionRepresentation,
                                          VoiceChannelOptionRepresentation)
from libs.serverconfig.options_list import options as options_list


async def autocomplete_main(bot: Axobot, interaction: Interaction, option: str, current: str):
    """Main autocompletion function, calling other sub-functions as needed"""
    if option not in options_list:
        return []
    option_data = options_list[option]
    option_data["option_name"] = option
    if option_data["type"] == "int":
        return await _autocomplete_integer(bot, interaction, option_data, current)
    if option_data["type"] == "float":
        return await _autocomplete_float(bot, interaction, option_data, current)
    if option_data["type"] == "boolean":
        return await _autocomplete_boolean(bot, interaction, option_data, current)
    if option_data["type"] == "enum":
        return await _autocomplete_enum(bot, interaction, option_data, current)
    if option_data["type"] == "text":
        return await _autocomplete_text(bot, interaction, option_data, current)
    if option_data["type"] == "role":
        return await _autocomplete_role(bot, interaction, option_data, current)
    if option_data["type"] == "text_channel":
        return await _autocomplete_text_channel(bot, interaction, option_data, current)
    if option_data["type"] == "voice_channel":
        return await _autocomplete_voice_channel(bot, interaction, option_data, current)
    if option_data["type"] == "category":
        return await _autocomplete_category(bot, interaction, option_data, current)
    if option_data["type"] == "emojis_list":
        return await _autocomplete_emojis_list(bot, interaction, option_data, current)
    if option_data["type"] == "levelup_channel":
        return await _autocomplete_levelup_channel(bot, interaction, option_data, current)
    return []


async def _autocomplete_integer(_bot: Axobot, _interaction: Interaction, option: IntOptionRepresentation, current: str):
    "Autocompletion for integer options"
    if not current.isnumeric():
        return []
    value = int(current)
    if value < option["min"]:
        return [Choice(name=str(option["min"]), value=str(option["min"]))]
    if value > option["max"]:
        return [Choice(name=str(option["max"]), value=str(option["max"]))]
    return [Choice(name=str(value), value=str(value))]


async def _autocomplete_float(_bot: Axobot, _interaction: Interaction, option: FloatOptionRepresentation, current: str):
    "Autocompletion for float options"
    try:
        value = round(float(current), 3)
    except ValueError:
        return []
    if value < option["min"]:
        return [Choice(name=str(option["min"]), value=str(option["min"]))]
    if value > option["max"]:
        return [Choice(name=str(option["max"]), value=str(option["max"]))]
    return [Choice(name=str(value), value=str(value))]

async def _autocomplete_boolean(_bot: Axobot, _interaction: Interaction, _option: BooleanOptionRepresentation, current: str):
    "Autocompletion for boolean options"
    possibilities = ("true", "false")
    if current:
        filtered = sorted(
            (not value.startswith(current), value)
            for value in possibilities
            if current in value
        )
        return [
            Choice(name=_T("server.bool."+value, default=value), value=value)
            for _, value in filtered
        ]
    return [
        Choice(name=_T("server.bool."+value, default=value), value=value)
        for value in possibilities
    ]

async def _autocomplete_enum(_bot: Axobot, _interaction: Interaction, option: EnumOptionRepresentation, current: str):
    "Autocompletion for enum options"
    tr_key = f"server.enum.{option['option_name']}."
    if current:
        filtered = sorted(
            (not value.startswith(current), value)
            for value in option["values"]
            if current in value
        )
        choices = [
            Choice(name=_T(tr_key+value, default=value), value=value)
            for _, value in filtered
        ]
    else:
        choices = [
            Choice(name=_T(tr_key+value, default=value), value=value)
            for value in option["values"]
        ]
    return choices[:25]


async def _autocomplete_text(_bot: Axobot, _interaction: Interaction, _option: TextOptionRepresentation, _current: str):
    "Autocompletion for text options"
    return []


async def _autocomplete_role(_bot: Axobot, interaction: Interaction, option: RoleOptionRepresentation, current: str):
    "Autocompletion for role options"
    filtered_roles = (
        role
        for role in interaction.guild.roles
        if (option["allow_integrated_roles"] or not role.is_integration())
        and (option["allow_everyone"] or not role.is_default())
    )
    if current:
        current = current.lower()
        roles = sorted(
            (not role.name.lower().startswith(current), role.name.lower(), role.name, str(role.id))
            for role in filtered_roles
            if current.lower() in role.name.lower() or current == str(role.id)
        )
        choices = [
            Choice(name=(name if name.startswith('@') else '@'+name), value=value)
            for _, _, name, value in roles
        ]
    else:
        roles = sorted(
            (role.name.lower(), role.name, str(role.id))
            for role in filtered_roles
        )
        choices = [
            Choice(name=(name if name.startswith('@') else '@'+name), value=value)
            for _, name, value in roles
        ]
    return choices[:25]


async def _autocomplete_text_channel(_: Axobot, interaction: Interaction, option: TextChannelOptionRepresentation, current: str):
    "Autocompletion for text channel options"
    all_channels: list[Union[discord.TextChannel, discord.Thread]] = interaction.guild.text_channels
    if option["allow_threads"]:
        all_channels += list(interaction.guild.threads)
    filtered_channels = (
        channel
        for channel in all_channels
        if (option["allow_threads"] or not isinstance(channel, discord.Thread))
        and (option["allow_announcement_channels"] or not channel.is_news())
        and (option["allow_non_nsfw_channels"] or channel.is_nsfw())
    )
    if current:
        current = current.lower()
        channels = sorted(
            (not channel.name.startswith(current), channel.name.lower(), channel.name, str(channel.id))
            for channel in filtered_channels
            if current.lower() in channel.name.lower() or current == str(channel.id)
        )
        choices = [Choice(name='#'+name, value=value) for _, _, name, value in channels]
    else:
        channels = sorted(
            (channel.name.lower(), channel.name, str(channel.id))
            for channel in filtered_channels
        )
        choices = [Choice(name='#'+name, value=value) for _, name, value in channels]
    return choices[:25]


async def _autocomplete_voice_channel(_: Axobot, interaction: Interaction, option: VoiceChannelOptionRepresentation, current:str):
    "Autocompletion for voice channel options"
    all_channels: list[Union[discord.VoiceChannel, discord.StageChannel]] = interaction.guild.voice_channels
    if option["allow_stage_channels"]:
        all_channels = all_channels + interaction.guild.stage_channels
    filtered_channels = (
        channel
        for channel in all_channels
        if (option["allow_stage_channels"] or not isinstance(channel, discord.StageChannel))
        and (option["allow_non_nsfw_channels"] or channel.is_nsfw())
    )
    if current:
        channels = sorted(
            (not channel.name.startswith(current), channel.name.lower(), channel.name, str(channel.id))
            for channel in filtered_channels
            if current.lower() in channel.name.lower() or current == str(channel.id)
        )
        choices = [Choice(name=name, value=value) for _, _, name, value in channels]
    else:
        channels = sorted(
            (channel.name.lower(), channel.name, str(channel.id))
            for channel in filtered_channels
        )
        choices = [Choice(name=name, value=value) for _, name, value in channels]
    return choices[:25]


async def _autocomplete_category(_: Axobot, interaction: Interaction, _option: CategoryOptionRepresentation, current: str):
    "Autocompletion for category options"
    if current:
        categories = sorted(
            (not category.name.startswith(current), category.name.lower(), category.name, str(category.id))
            for category in interaction.guild.categories
            if current.lower() in category.name.lower() or current == str(category.id)
        )
        choices = [Choice(name=name, value=value) for _, _, name, value in categories]
    else:
        categories = sorted(
            (category.name.lower(), category.name, str(category.id))
            for category in interaction.guild.categories
        )
        choices = [Choice(name=name, value=value) for _, name, value in categories]
    return choices[:25]


async def _autocomplete_emojis_list(_: Axobot, interaction: Interaction, option: EmojisListOptionRepresentation, current: str):
    "Autocompletion for emojis list options"
    if current:
        if " " in current:
            typed_emojis = current.split(" ")
            if len(typed_emojis) > option["max_count"]:
                truncated_current = " ".join(typed_emojis[:option["max_count"]])
                return [Choice(name=truncated_current, value=truncated_current)]
            current = typed_emojis[-1]
            previous = " ".join(typed_emojis[:-1]) + " "
        else:
            previous = ""
        current = current.strip(":").lower()
        emojis = sorted(
            (not emoji.name.lower().startswith(current), emoji.name.lower(), ':'+emoji.name+':', str(emoji.id))
            for emoji in interaction.guild.emojis
            if current.lower() in emoji.name.lower() or current == str(emoji.id)
        )
        choices = [Choice(name=previous + name, value=previous + value) for _, _, name, value in emojis]
    else:
        emojis = sorted(
            (emoji.name.lower(), ':'+emoji.name+':', str(emoji.id))
            for emoji in interaction.guild.emojis
        )
        choices = [Choice(name=name, value=value) for _, name, value in emojis]
    return choices[:25]


async def _autocomplete_levelup_channel(_bot: Axobot, interaction: Interaction,
                                        _option: LevelupChannelOptionRepresentation, current: str):
    "Autocompletion for the levelup channel option"
    special_values = ("any", "none", "dm")
    if current:
        channels = sorted(
            (not channel.name.startswith(current), channel.name.lower(), channel.name, str(channel.id))
            for channel in interaction.guild.text_channels
            if current.lower() in channel.name.lower() or current == str(channel.id)
        )
        choices = [Choice(name=name, value=value) for _, _, name, value in channels][:23]
        for value in special_values:
            value_name = _T("server.enum.levelup_channel." + value, default=value)
            if value.startswith(current):
                choices = [Choice(name=value_name, value=value)] + choices
            else:
                choices.append(Choice(name=value_name, value=value))
    else:
        channels = sorted(
            (channel.name.lower(), channel.name, str(channel.id))
            for channel in interaction.guild.text_channels
        )
        choices = [
            Choice(name=_T("server.enum.levelup_channel." + value, default=value), value=value)
            for value in special_values
        ]
        choices += [Choice(name='#'+name, value=value) for _, name, value in channels]
    return choices[:25]
