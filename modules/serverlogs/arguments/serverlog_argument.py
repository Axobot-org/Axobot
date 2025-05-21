from discord import app_commands

from core.arguments.errors import InvalidServerLogError

LOGS_CATEGORIES = {
    "automod": {"antiraid", "antiscam"},
    "members": {"member_roles", "member_nick", "member_avatar", "member_join", "member_leave",
                "member_verification", "user_update"},
    "moderation": {"clear", "member_ban", "member_unban", "member_timeout", "member_kick", "member_warn",
                    "moderation_case", "slowmode"},
    "messages": {"message_update", "message_delete", "discord_invite", "ghost_ping"},
    "other": {"bot_warnings", "react_usage", "say_usage", "server_update"},
    "roles": {"role_creation", "role_update", "role_deletion"},
    "tickets": {"ticket_creation"},
    "voice": {"voice_join", "voice_move", "voice_leave"}
}

ALL_LOGS = {log for category in LOGS_CATEGORIES.values() for log in category}

class ServerLogTransformer(app_commands.Transformer): # pylint: disable=abstract-method
    "Convert arguments to a server log type"

    async def transform(self, _interaction, value: str, /):
        "Do the conversion"
        if value == "all":
            return list(ALL_LOGS)
        result: list[str] = []
        for word in value.split(" "):
            if word not in ALL_LOGS:
                raise InvalidServerLogError(value)
            result.append(word)
        if len(result) == 0:
            raise InvalidServerLogError(value)
        return result

ServerLogArgument = app_commands.Transform[list[str], ServerLogTransformer]
