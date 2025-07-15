import re

_MKD_LINE_BEGINNING = r"^([#>]{1,3} ?)(?P<lb_text>\S+)"
_MKD_CODE = r"(`+)(?P<code_text>[^`]+)(`+)"
_MKD_UNDERSCORE = r"(_+)(?P<underscore_text>[^_\n]+)(_+)"
_MKD_ASTERISK = r"(\*+)(?P<asterisk_text>[^*\n]+)(\*+)"
_MKD_SPOILER = r"(\|\|)(?P<spoiler_text>[^|\n]+)(\|\|)"
_MKD_TILDE = r"(~~)(?P<tilde_text>[^~\n]+)(~~)"
_MKD_FULL_REGEX = re.compile(
    "(?:" +
    '|'.join([
        _MKD_LINE_BEGINNING,
        _MKD_CODE,
        _MKD_UNDERSCORE,
        _MKD_ASTERISK,
        _MKD_SPOILER,
        _MKD_TILDE,
    ])
     + ')',
    flags=re.MULTILINE
)

def _replacement(match: re.Match[str]) -> str:
    """Replace a markdown match with its content"""
    for text in match.groupdict().values():
        if text:
            return text
    return ""

def remove_markdown(source: str):
    return _MKD_FULL_REGEX.sub(_replacement, source)

_ANY_LINK_PATTERN = re.compile(r"(https?://?(?:[-\w.]|(?:%[\da-fA-F]{2}))+|discord.gg/[^\s]+)")
def sync_check_any_link(text: str):
    "Check if a text contains a http url"
    return _ANY_LINK_PATTERN.search(text)

_DISCORD_INVITE_PATTERN = re.compile(r"((?:discord\.gg|discord(?:app)?.com/invite|discord.me)/.+)")
def sync_check_discord_invite(text: str):
    "Check if a text contains a discord invite url"
    return _DISCORD_INVITE_PATTERN.search(text)
