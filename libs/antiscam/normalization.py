import os
import re
from json import load

from emoji.unicode_codes import get_aliases_unicode_dict
from nltk import SnowballStemmer
from nltk.corpus import stopwords

UNICODE_EMOJI: dict[str, str] = get_aliases_unicode_dict()

RE_EMAIL = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
RE_WEB = re.compile(
    r'https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#= ]{1,256}\.[ a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&/=]*)')
RE_MONEY = re.compile(r'£|\$|€')
RE_PHONE = re.compile(
    r'\D((?:(?:\+|00)33|0)\s*[\d](?:[\s.-]*\d{2}){4}|(?:0|\+?44)\s?(?:\d\s?){9,10}\d)(?!\d)')
RE_NUMBER_DOT = re.compile(r'((?:\d{1,3}(?:,\d{3})*|\d+)(?:[\.]\d+)?)(?=\D|$)')
RE_PUNCTUATION = re.compile(r'(?:[^\w\d\s]|_)+')
RE_PUNCTUATION_NO_DOTS = re.compile(r'(?:[^\w\d\s\.\!\?]|_)+')
RE_DOTS = re.compile(r'[\.\!\?]+')
RE_MULTIPLE_WHITESPACES = re.compile(r'\s{2,}')
RE_LEADING_WHITESPACES = re.compile(r'^\s+|\s*?$')
RE_DISCORD_USER = re.compile(r'<@!?\d{15,}>')
RE_DISCORD_ROLE = re.compile(r'<@&\d{15,}>')
RE_DISCORD_EMOJI = re.compile(r'<a?:\w+:\d+>')
RE_DISCORD_CHANNEL = re.compile(r'<#&?\d{15,}>')
RE_DISCORD_INVITE = re.compile(r'(https?://)?(www\.)?(discord\.(gg|io|me|li)|discordapp\.com/invite)/ ?[\w-]{3,}')
RE_DISCORD_ID = re.compile(r'(?:\D|^)(\d{17,19})(?:\D|$)')

STOP_WORDS = set(stopwords.words('english'))
AFFIXES_STEM = SnowballStemmer("english")
PROTECTED_WORDS = ('discordchannel', 'discorduser', 'discordemoji', 'discordrole', 'discordid',
                   'emailaddress', 'webaddress', 'phonenumber', 'moneysymbol', 'number', 'discordinvite', 'emoji')

with open(os.path.dirname(__file__)+'/data/unicode_map.json', 'r', encoding='utf-8') as file:
    UNICODE_MAP: dict[str, str] = load(file)

emojis_iter = map(lambda y: y, UNICODE_EMOJI.keys())
RE_EMOJI = re.compile('|'.join(re.escape(em) for em in emojis_iter))


def normalize(message: str) -> str:
    message = normalize_unicode(message)
    message = normalize_emojis(message)
    message = normalize_words(message)
    message = normalize_chars(message, remove_dots=False)
    message = message.lower()
    message = normalize_stopwords(message)
    message = normalize_affixes(message)
    return message


def normalize_emojis(message: str) -> str:
    return RE_EMOJI.sub(' emoji ', message)

def normalize_words(message: str) -> str:
    message = RE_DISCORD_INVITE.sub(' discordinvite ', message)

    message = RE_EMAIL.sub(' emailaddress ', message)
    message = RE_WEB.sub(' webaddress ', message)
    message = RE_MONEY.sub(' moneysymbol ', message)

    message = RE_DISCORD_USER.sub(' discorduser ', message)
    message = RE_DISCORD_ROLE.sub(' discordrole ', message)
    message = RE_DISCORD_EMOJI.sub(' discordemoji ', message)
    message = RE_DISCORD_CHANNEL.sub(' discordchannel ', message)
    message = RE_DISCORD_ID.sub('\\1 discordid \\2', message)

    message = RE_PHONE.sub(' phonenumber ', message)
    message = RE_NUMBER_DOT.sub(' number ', message)
    return message

def normalize_chars(message: str, remove_dots: bool = True) -> str:
    if remove_dots:
        message = RE_PUNCTUATION.sub(' ', message)
    else:
        message = RE_PUNCTUATION_NO_DOTS.sub(' ', message)
        for match in RE_DOTS.finditer(message):
            message = message.replace(match.group(0), f" {match.group(0)} ")
    message = RE_MULTIPLE_WHITESPACES.sub(' ', message)
    message = RE_LEADING_WHITESPACES.sub(' ', message)
    return message.strip()


def normalize_stopwords(message: str) -> str:
    return ' '.join(term for term in message.split() if term in PROTECTED_WORDS or term not in STOP_WORDS)


def normalize_affixes(message: str) -> str:
    return ' '.join(term if term in PROTECTED_WORDS else AFFIXES_STEM.stem(term) for term in message.split())

def normalize_unicode(message: str) -> str:
    new_msg = ''
    for c in message:
        if c.isascii() or c in {' ', '€'}:
            new_msg += c
        else:
            hex_repr = f"{ord(c):04x}".upper()
            if ' ' not in UNICODE_MAP.get(hex_repr, ' '): # both check for existence and unicity
                new_msg += chr(int(UNICODE_MAP.get(hex_repr), 16))
            else:
                new_msg += c
    return new_msg
