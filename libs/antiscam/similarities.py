import csv
from difflib import SequenceMatcher
import os
from re import finditer

from .normalization import normalize_unicode

WHITELISTED_WEBSITES: list[str] = []
BLACKLISTED_WEBSITES: list[str] = []

with open(os.path.dirname(__file__)+'/data/base_websites.csv', 'r', encoding='utf-8') as csv_file:
    spamreader = csv.reader(csv_file)
    for row in spamreader:
        if row[0] == '1':
            BLACKLISTED_WEBSITES.append(row[1])
        else:
            WHITELISTED_WEBSITES.append(row[1])


def _similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def check_message(message: str) -> int:
    score = 0
    message = normalize_unicode(message)
    for link in search_links(message):
        link = ".".join(link.split('.')[-2:])
        score += check_url_similarity(link)
    return max(score,0)

def check_url_similarity(url: str):
    matching_score = 0
    url = url.replace(' ', '').lower().strip()
    # print('ANALYZING', url)
    if url == 'discord.gg':
        return -2
    if url in WHITELISTED_WEBSITES:
        return - 10
    if url in {'bit.ly', 'cutt.ly', 'tinyurl.com'}:
        return 1
    
    for sim in BLACKLISTED_WEBSITES:
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

    for sim in WHITELISTED_WEBSITES:
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
    print(check_message("""Free discord nitro for 1 month!
https://discord-gg.com/nitro @everyone"""))
    print(check_message("'@everyone 🤩Hey, steam gived nitro - https://dicsord.club/classic"))