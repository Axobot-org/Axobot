from difflib import SequenceMatcher
from re import finditer, sub, IGNORECASE

from .normalization import normalize_unicode


def _similar(input_1: str, input_2: str):
    "Compare two strings and output the similarity ratio"
    return SequenceMatcher(None, input_1, input_2).ratio()

def check_message(message: str, websites_reference: dict[str, bool]) -> int:
    "Check every URL in a message and return the sum of each URL's score"
    score = 0
    message = normalize_unicode(message)
    message = sub(r'(\S)\(dot\)(\S)', r'\1.\2', message, flags=IGNORECASE)
    for link in search_links(message):
        link = ".".join(link.split('.')[-2:])
        score += check_url_similarity(link, websites_reference)
    return max(score, 0)

def check_url_similarity(url: str, websites_reference: dict[str, bool]):
    "Check an URL similarity to known safe or dangerous websites"
    matching_score = 0
    url = url.replace(' ', '').lower().strip()
    # print('ANALYZING', url)
    if url == 'discord.gg':
        return -2
    if websites_reference.get(url, False):
        return - 10
    if url in {'bit.ly', 'cutt.ly', 'tinyurl.com'}:
        return 1

    for sim in (key for key, value in websites_reference.items() if not value):
        if url == sim:
            matching_score += 5
            break
        seq = _similar(url, sim)
        # print('  SIMILAR AT', round(seq,3), 'TO', sim)
        if seq >= 0.85:
            matching_score += 3
        elif seq >= 0.75:
            matching_score += 2
        elif seq >= 0.7:
            matching_score += 1

    if url.endswith('.ru'):
        matching_score += 1

    if matching_score > 1:
        return matching_score

    for sim in (key for key, value in websites_reference.items() if value):
        seq = _similar(url, sim)
        # print('  SIMILAR AT', round(seq,3), 'TO', sim)
        if seq >= 0.85:
            matching_score += 3
        elif seq >= 0.75:
            matching_score += 2
        elif seq >= 0.7:
            matching_score += 1

    return matching_score

def search_links(message: str):
    return map(lambda x: x.group(1), finditer(r'([.\w_-]+\.\w{2,7})(/[/\S]{3,})?\b', message))

if __name__ == '__main__':
    websites_refs = {
        'discord.gg': True,
        'discord.com': True,
        'discordapp.com': True,
        'discord.me': True,
        'discord.io': True,
        'twitter.com': True,
        'youtube.com': True,
        'youtu.be': True,
        'twitch.tv': True,
        'discord.store': False,
        'discord.gifts': False,
        'discord.net': False,
        'steamnitro.co': False,
        'free-nitro.ru': False,
        'discord-beta.com': False,
    }
    print(check_message("""Free discord nitro for 1 month!
https://discord-gg.com/nitro @everyone""", websites_refs))
    print(check_message("'@everyone 🤩Hey, steam gived nitro - https://dicsord.club/classic", websites_refs))
