import re
from collections import Counter
from typing import TypeVar

from .normalization import normalize
from .similarities import check_message


def get_mentions_count(msg: str):
    return len(re.findall(r'<@!?\d{15,}>', msg))

def get_max_frequency(msg: str):
    counter = Counter(msg.replace(' ', '').lower())
    s = sum(counter.values())
    return round(max(v/s for v in counter.values()), 4)

def get_punctuation_count(msg: str):
    counter = 0
    for c in msg:
        if c in {'.', '!', '?'}:
            counter += 1
    return counter

def get_caps_count(msg: str):
    counter = 0
    for c in msg:
        if c != c.lower():
            counter += 1
    return counter

def get_avg_word_len(msg: str):
    lengths = [len(word) for word in msg.split(' ')]
    return sum(lengths) / len(lengths)

class Message:
    def __init__(self, message: str, normd_message: str, contains_everyone: bool, url_score: int, mentions_count: int, max_frequency: float, punctuation_count: int, caps_percentage: float, avg_word_len: float, category: int):
        self.message = message
        self.normd_message = normd_message
        self.contains_everyone = contains_everyone
        self.url_score = url_score
        self.mentions_count = mentions_count
        self.max_frequency = max_frequency
        self.punctuation_count = punctuation_count
        self.caps_percentage = caps_percentage
        self.avg_word_len = avg_word_len
        self.category = category

    @classmethod
    def from_raw(cls, raw_message: str, mentions_count: int):
        normd_message = normalize(raw_message)
        contains_everyone = '@everyone' in raw_message
        url_score = check_message(raw_message)
        max_frequency = get_max_frequency(raw_message)
        punctuation_count = get_punctuation_count(raw_message)
        caps_percentage = get_caps_count(raw_message)/len(raw_message)
        avg_word_len = get_avg_word_len(normd_message)
        return cls(raw_message, normd_message, contains_everyone, url_score, mentions_count, max_frequency, punctuation_count, caps_percentage, avg_word_len, 0)

    def to_dict(self):
        return {
            'message': self.message,
            'normd_message': self.normd_message,
            'contains_everyone': self.contains_everyone,
            'url_score': self.url_score,
            'mentions_count': self.mentions_count,
            'max_frequency': self.max_frequency,
            'punctuation_count': self.punctuation_count,
            'caps_percentage': self.caps_percentage,
            'avg_word_len': self.avg_word_len,
            'category': self.category
        }

    def to_data_dict(self):
        return {
            'message': self.normd_message,
            'contains_everyone': self.contains_everyone,
            'url_score': self.url_score,
            'length': len(self.normd_message),
            'mentions_count': self.mentions_count,
            'max_frequency': self.max_frequency,
            'punctuation_count': self.punctuation_count,
            'caps_percentage': self.caps_percentage,
            'avg_word_len': self.avg_word_len,
            'class': self.category
        }

ClassType = TypeVar('ClassType')
class PredictionResult:
    def __init__(self, probabilities: list[float], classes: list[ClassType]):
        self.probabilities: dict[ClassType, float] = dict()
        self.result: ClassType = None
        max_prob = -1
        for prob, cls in zip(probabilities, classes):
            self.probabilities[cls] = prob
            if prob > max_prob:
                self.result = cls
                max_prob = prob
        self.classes = classes

    def to_dict(self):
        return {
            'probabilities': self.probabilities,
            'result': self.result,
            'classes': self.classes
        }

    def to_string(self, categories: dict):
        probas = '\n    - '.join(f'{categories[c]}: {round(p,3)}' for c, p in self.probabilities.items())
        return f"""Result: {categories[self.result]}

Probabilities:
    - {probas}
        """
