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

=============
Release notes
=============
"""
    for note in data:
        text += "\n" + _generate_version_note(note) + "\n"
    return text.rstrip()

def _generate_version_note(note: VersionNote):
    "Create a reStructuredText section for a given version note"
    # cleanup spaces
    content = _strip_lines(note["content"])
    # extract the version number
    try:
        version = re.search(r"Update (\d+\.\d+\.\d+)", content).group(1)
    except AttributeError:
        return _convert_to_rst(content)
    # extract the section titles and contents
    sections: list[tuple[str, str]] = []
    for match in re.finditer(r"\n\n(?:## |__)(?P<title>[^\n_]+)_{0,2}\n(?P<content>(?:.+|\n\*)+)", content):
        sections.append((
            match.group("title").strip(),
            _convert_to_rst(match.group("content"))
        ))
    # create the reStructuredText section
    text = f"""
{version}
{'=' * len(version)}

*Released on {note["release_date"]}*

"""
    for title, content in sections:
        text += f"**{title}**\n\n{content}\n\n"
    return text.rstrip()

def _strip_lines(text: str):
    "Strip leading and trailing whitespace from every line in a string"
    return "\n".join(line.strip() for line in text.splitlines())

def _convert_to_rst(text: str):
    "Convert a markdown release note to reStructuredText format"
    # convert markdown inline code
    text = re.sub(r"`([^`]+)`", r"``\1``", text)
    # convert markdown links
    text = re.sub(r"\[([^\]]+)\]\(<?([^>)]+)>?\)", r"`\1 <\2>`__", text)
    return text

if __name__ == "__main__":
    print(_generate_changelog_text())
