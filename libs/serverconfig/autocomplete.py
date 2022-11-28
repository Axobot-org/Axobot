from discord import Interaction
from discord.app_commands import Choice

from libs.bot_classes import Zbot

from . import options_list

async def autocomplete_main(bot: Zbot, interaction: Interaction, option: str, current: str) -> list[Choice]:
    """Main autocompletion function, calling other sub-functions as needed"""
    if option in options_list.roles_options:
        return await autocomplete_roles(interaction, current)
    if option in options_list.voicechannels_options:
        return await autocomplete_vocchan(interaction, current)
    if option in options_list.bool_options:
        return await autocomplete_bool(interaction, current)
    if option == "language":
        return await autocomplete_language(bot, interaction, current)
    if option in options_list.raid_options:
        return await autocomplete_raid(bot, interaction, current)
    if option in options_list.xp_type_options:
        return await autocomplete_xp_type(bot, interaction, current)
    if option in options_list.ttt_display_option:
        return await autocomplete_ttt_mode(bot, interaction, current)
    return []


async def autocomplete_roles(interaction: Interaction, current: str) -> list[Choice]:
    "Autocomplete a role"
    roles = [
        (role.name, str(role.id)) for role in interaction.guild.roles
        if current.lower() in role.name.lower() or current == str(role.id)
    ]
    return [
        Choice(name=name, value=id) for name, id in roles
    ]

async def autocomplete_vocchan(interaction: Interaction, current: str) -> list[Choice]:
    "Autocomplete a voice channel"
    channels = [
        (channel.name, str(channel.id)) for channel in interaction.guild.voice_channels
        if current.lower() in channel.name.lower() or current == str(channel.id)
    ]
    return [
        Choice(name=name, value=id) for name, id in channels
    ]

async def autocomplete_bool(_interaction: Interaction, _current: str):
    "Autocomplete a boolean"
    return [
        Choice(name="True", value="1"),
        Choice(name="False", value="0"),
    ]

async def autocomplete_language(bot: Zbot, _interaction: Interaction, current: str):
    "Autocomplete a language"
    languages: list[str] = bot.get_cog("Languages").languages
    if current:
        return [
            Choice(name=language, value=language) for language in languages
            if language.startswith(current)
        ]
    return [
        Choice(name=language, value=language) for language in languages
    ]

async def autocomplete_raid(bot: Zbot, _interaction: Interaction, current: str):
    "Autocomplete a raid protection level"
    levels = bot.get_cog("Servers").raids_levels
    if current:
        return [
            Choice(name=level, value=level) for level in levels
            if level.lower().startswith(current.lower())
        ]
    return [
        Choice(name=level, value=level) for level in levels
    ]

async def autocomplete_xp_type(bot: Zbot, _interaction: Interaction, current: str):
    "Autocomplete a xp type"
    types = bot.get_cog('Xp').types
    if current:
        return [
            Choice(name=type_name, value=type_name) for type_name in types
            if type_name.startswith(current)
        ]
    return [
        Choice(name=type_name, value=type_name) for type_name in types
    ]

async def autocomplete_ttt_mode(bot: Zbot, _interaction: Interaction, current: str):
    "Autocomplete a tic-tac-toe display mode"
    types: list[str] = bot.get_cog("Morpions").types
    if current:
        return [
            Choice(name=type_name, value=type_name) for type_name in types
            if type_name.lower().startswith(current.lower())
        ]
    return [
        Choice(name=type_name, value=type_name) for type_name in types
    ]
