import re
from typing import TypedDict

import requests

CHANGELOG_URL = "https://api.zrunner.me/discord/changelog?language=en"

def generate_changelog_file(filename: str):
    "Generate the changelog file for the documentation"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(_generate_changelog_text())

class VersionNote(TypedDict):
    "A JSON object representing a version note"
    version: str
    release_date: str
    content: str

def _generate_changelog_text():
    "Generate the changelog for the documentation"
    response = requests.get(CHANGELOG_URL, timeout=20)
    response.raise_for_status()
    data: list[VersionNote] = response.json()
    text = """:og:description: Find here the list of every release of Axobot!
:html_theme.sidebar_secondary.remove:

================
📰 Release notes
================
"""
    for note in data:
        text += "\n" + _generate_version_note(note) + "\n"
    return text.rstrip()

def _generate_version_note(note: VersionNote):
    "Create a reStructuredText section for a given version note"
    # cleanup spaces
    content = _strip_lines(note["content"])
    # extract the version number
    version = note.get("version") or _extract_version(content)
    # format the release date
    date = _format_date(note["release_date"])
    # extract the section titles and contents
    sections: list[tuple[str, str]] = []
    current_title: str | None = None
    current_lines: list[str] = []
    for line in content.splitlines():
        stripped_line = line.strip()
        heading_match = re.match(r"^(?:##|__)\s*(?P<title>[^\n_]+?)\s*_*$", stripped_line)
        if heading_match is None:
            heading_match = re.match(r"^\*\*(?P<title>.+?)\*\*\s*$", stripped_line)
        if heading_match is not None:
            if current_title is not None:
                sections.append((current_title, _convert_to_rst("\n".join(current_lines))))
            current_title = heading_match.group("title").strip()
            current_lines = []
            continue
        if current_title is not None or not sections:
            current_lines.append(line)
    if current_title is not None:
        sections.append((current_title, _convert_to_rst("\n".join(current_lines))))
    elif current_lines:
        sections.append((version, _convert_to_rst("\n".join(current_lines))))

    # remove a bold English "Update X.Y.Z" title from the generated output if present
    header_line = next(
        (
            title
            for title, _ in sections
            if re.fullmatch(r"(?:\*\*)?Update \d+\.\d+\.\d+[^\n\*]*(?:\*\*)?", title, flags=re.IGNORECASE)
        ),
        None,
    )
    if header_line is not None:
        sections = [
            (version if title == header_line else title, body)
            for title, body in sections
        ]
    # create the reStructuredText section
    anchor = re.sub(r"[^A-Za-z0-9_.-]+", "-", version).strip("-")
    text = f"""

.. _v{anchor}:

{version}
{'=' * len(version)}

*Released on {date}*

"""
    for title, content in sections:
        if title == version:
            text += f"{content}\n\n"
        else:
            text += f"**{title}**\n\n{content}\n\n"
    return text.rstrip()

def _extract_version(content: str) -> str:
    if (match := re.search(
        r"(?:^|\s)(?:\*\*)?Update(?:\*\*)?\s+(\d+\.\d+\.\d+[a-z]?)",
        content,
        flags=re.IGNORECASE,
    )) is not None:
        return match.group(1)
    if (match := re.search(r"(?:^|\s)(?:\*\*)?(\d+\.\d+\.\d+[a-z]?)(?:\*\*)?", content)) is not None:
        return match.group(1)
    return "?"

def _strip_lines(text: str):
    "Strip trailing whitespace while preserving list indentation in each line"
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()

def _format_date(raw_date: str):
    "Format a date in the ISO format to the more readable year-month-day format"
    return raw_date.split("T")[0]

def _convert_to_rst(text: str):
    "Convert a markdown release note to reStructuredText format"
    # convert markdown links and inline code in a single pass
    # (rst does not support inline code inside a link, so backticks are dropped from link labels)
    def _replace(match: re.Match[str]):
        if match.group("label") is not None:
            label = match.group("label").replace("`", "")
            return f"`{label} <{match.group('url')}>`__"
        return f"``{match.group('code')}``"
    text = re.sub(
        r"\[(?P<label>[^\]]+)\]\(<?(?P<url>[^>)\s]+)>?\)|`(?P<code>[^`]+)`",
        _replace,
        text,
    )
    # convert discord custom emojis
    text = re.sub(r"<a?:(\w+):\d+>", '', text)
    # convert discord command mentions
    text = re.sub(r"</([\w ]+):\d+>", r"``/\1``", text)

    lines = text.splitlines()
    converted_lines: list[str] = []
    for index, line in enumerate(lines):
        if not line.strip():
            converted_lines.append("")
            continue

        indent_len = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if re.match(r"^[-*]\s+", stripped):
            if indent_len > 0 and converted_lines and converted_lines[-1].strip():
                converted_lines.append("")
            line_without_bullet = re.sub(r'^[-*]\s+', '', stripped)
            converted_lines.append(f"{'  ' * (indent_len // 2)}* {line_without_bullet}")
            next_line = lines[index + 1] if index + 1 < len(lines) else ""
            if next_line.strip() and (len(next_line) - len(next_line.lstrip(" ")) <= indent_len):
                converted_lines.append("")
        else:
            converted_lines.append(line.rstrip())

    return "\n".join(converted_lines)

if __name__ == "__main__":
    print(_generate_changelog_text())
