import logging

from bs4 import BeautifulSoup

log = logging.getLogger("bot.rss")

async def get_text_from_entry(entry: dict) -> str | None:
    "Get the text from an RSS feed entry"
    if "content" in entry:
        return await convert_post_to_text(entry["content"][0]["value"], entry["content"][0]["type"])
    if "summary" in entry:
        if "summary_detail" not in entry:
            return entry["summary"]
        return await convert_post_to_text(entry["summary"], entry["summary_detail"]["type"])
    log.error("No content or summary in entry for article %s", entry['link'])
    return None

async def get_summary_from_entry(entry: dict) -> str | None:
    "Get the summary from an RSS feed entry"
    if "content" in entry and "summary" in entry: # if summary is the actual content, it's not the summary duh
        if "summary_detail" not in entry:
            return entry["summary"]
        return await convert_post_to_text(entry["summary"], entry["summary_detail"]["type"])
    log.warning("No summary in entry (or summary is same than content) for article %s", entry['link'])
    return None

async def convert_post_to_text(post: str, post_type: str) -> str | None:
    "Convert an RSS feed post text into a plain text string"
    if post_type == "text/html":
        return await convert_html_to_text(post)
    elif post_type == "text/plain":
        return post
    else:
        log.error("Unknown post type: %s", post_type)
        return None


async def convert_html_to_text(html: str) -> str:
    "Convert an HTML string into a plain text string"
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text()
