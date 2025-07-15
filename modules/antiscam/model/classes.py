import re
from collections import Counter
from typing import Generic, Iterable, Sequence, TypedDict, TypeVar

import discord

from .normalization import normalize
from .similarities import check_message


def get_mentions_count(msg: str):
    "Returns the number of user mentions in the message."
    return len(re.findall(r"<@!?\d{15,}>", msg))

def get_max_frequency(msg: str):
    "Returns the frequency of the most common character in the message, between 0 and 1, rounded to 4 decimals."
    counter = Counter(msg.replace(' ', '').lower())
    s = sum(counter.values())
    return round(max(v/s for v in counter.values()), 5)

def get_punctuation_count(msg: str):
    "Returns the number of punctuation characters in the message."
    counter = 0
    for c in msg:
        if c in {'.', '!', '?'}:
            counter += 1
    return counter

def get_caps_frequency(msg: str):
    "Returns the percentage of uppercase characters in the message, between 0 and 1."
    counter = 0
    for c in msg:
        if c != c.lower():
            counter += 1
    return round(counter / len(msg), 5)

def get_avg_word_len(msg: str):
    "Returns the average length of words in the message."
    lengths = [len(word) for word in msg.split(' ')]
    return round(sum(lengths) / len(lengths), 5)

EMBED_COLORS = {
    "pending": "#000",
    "deleted": "#0066ff",
    "harmless": "#bcc2c2",
    "scam": "#ffa31a",
    "raid": "#ff3333",
    "insults": "#cc33ff",
    "spam": "#ff1aff"
}

class Message:
    "Represents a potentially malicious message"

    def __init__(self, message: str, normd_message: str, contains_everyone: bool, url_score: int, mentions_count: int,
                 max_frequency: float, punctuation_count: int, caps_percentage: float, avg_word_len: float, category: int):
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
    def from_raw(cls, raw_message: str, mentions_count: int, websites_reference: dict[str, bool]):
        "Create a Message instance from a string"
        normd_message = normalize(raw_message)
        contains_everyone = "@everyone" in raw_message
        url_score = check_message(raw_message, websites_reference)
        max_frequency = get_max_frequency(raw_message)
        punctuation_count = get_punctuation_count(raw_message)
        caps_percentage = get_caps_frequency(raw_message)
        avg_word_len = get_avg_word_len(normd_message)
        return cls(raw_message, normd_message, contains_everyone, url_score, mentions_count, max_frequency, punctuation_count,
                   caps_percentage, avg_word_len, 0)

    def to_dict(self):
        return {
            "message": self.message,
            "normd_message": self.normd_message,
            "contains_everyone": self.contains_everyone,
            "url_score": self.url_score,
            "mentions_count": self.mentions_count,
            "max_frequency": self.max_frequency,
            "punctuation_count": self.punctuation_count,
            "caps_percentage": self.caps_percentage,
            "avg_word_len": self.avg_word_len,
            "category": self.category
        }

    def to_data_dict(self):
        return {
            "message": self.normd_message,
            "contains_everyone": self.contains_everyone,
            "url_score": self.url_score,
            "length": len(self.normd_message),
            "mentions_count": self.mentions_count,
            "max_frequency": self.max_frequency,
            "punctuation_count": self.punctuation_count,
            "caps_percentage": self.caps_percentage,
            "avg_word_len": self.avg_word_len,
            "class": self.category
        }

PredictionClass = TypeVar("PredictionClass")

class PredictionResultDict(TypedDict, Generic[PredictionClass]):
    "Represents the result of a prediction, as a dictionary"
    probabilities: dict[PredictionClass, float]
    result: PredictionClass | None
    classes: Sequence[PredictionClass]

class PredictionResult(Generic[PredictionClass]):
    "Represents the results of an AI prediction"
    def __init__(self, probabilities: Iterable[float], classes: Iterable[PredictionClass]):
        self.probabilities: dict[PredictionClass, float] = {}
        self.result: PredictionClass | None = None
        max_prob = -1
        for prob, cls in zip(probabilities, classes, strict=True):
            self.probabilities[cls] = prob
            if prob > max_prob:
                self.result = cls
                max_prob = prob
        self.classes = classes

    def to_dict(self) -> PredictionResultDict[PredictionClass]:
        "Returns a dictionary representation of the prediction result"
        return {
            "probabilities": self.probabilities,
            "result": self.result,
            "classes": list(self.classes)
        }

    def to_string(self, categories: dict[PredictionClass, str]) -> str:
        "Returns a string representation of the prediction result"
        if self.result:
            text = f"Result: {categories[self.result]}"
        else:
            text = "Result: Unknown"
        text += "\n\nProbabilities:\n"
        for category, proba in self.probabilities.items():
            text += f"- {categories[category]}: {round(proba*100, 1)}%\n"
        return text

class MsgReportView(discord.ui.View):
    "Embed view in the internal reports channel, used to confirm/deny/delete a message report"
    def __init__(self, row_id):
        super().__init__()
        for category in ("scam", "insults", "raid", "spam"):
            self.add_item(discord.ui.Button(
                label=f"Confirm {category}",
                style=discord.ButtonStyle.green,
                custom_id=f"{category}-{row_id}",
                row=0
            ))
        self.add_item(discord.ui.Button(
            label="Harmless message",
            style=discord.ButtonStyle.gray,
            emoji="👌",
            custom_id=f"harmless-{row_id}",
            row=1
        ))
        self.add_item(discord.ui.Button(
            label="Personal data message",
            style=discord.ButtonStyle.red,
            emoji="🗑",
            custom_id=f"delete-{row_id}",
            row=1
        ))
