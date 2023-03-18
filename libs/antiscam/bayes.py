import math
import os
import pickle
import re
import string
from typing import Literal, Optional, TypedDict
import random

from .classes import Message

CLASS = Literal[0, 1]

CUSTOM_ATTRS = {'contains_everyone', 'url_score', 'mentions_count',
                'punctuation_count', 'max_frequency', 'caps_percentage', 'avg_word_len'}

class RoundValueType(TypedDict):
    "Used to know how many decimals to round the values to"
    max_frequency: int
    caps_percentage: int
    avg_word_len: int


class SpamDetector:
    """Implementation of Naive Bayes for binary classification"""
    def __init__(self, round_values: RoundValueType):
        self.round_values = round_values
        self.num_messages: dict[str, int] = {}
        self.log_class_priors: dict[str, float] = {}
        self.attr_counts: dict[str, dict[str, int]] = {}
        self.classes_: dict[int, int] = {}
        # list of all words
        self.vocab = set()

    def clean(self, s: str):
        translator = str.maketrans("", "", string.punctuation)
        return s.translate(translator)

    def tokenize(self, text: str) -> list[str]:
        text = self.clean(text).lower()
        return [x for x in re.split("\W+", text) if x]

    def get_word_counts(self, words: list[str]) -> dict[str, int]:
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        return word_counts

    def fit(self, data: list[Message]):
        "X is the documents list, Y is the labels list"
        n = len(data)
        # number of spam messages
        self.num_messages['spam'] = sum(1 for record in data if record.category == 1)
        # number of ham messages
        self.num_messages['ham'] = sum(1 for record in data if record.category == 0)
        # proba that a given message is spam
        self.log_class_priors['spam'] = math.log(self.num_messages['spam'] / n)
        # proba that a given message is ham
        self.log_class_priors['ham'] = math.log(self.num_messages['ham'] / n)
        # words frequency in spam messages
        self.attr_counts['spam'] = {}
        # words frequency in ham messages
        self.attr_counts['ham'] = {}

        for record in data:
            c = 'spam' if record.category == 1 else 'ham'
            counts = self.get_word_counts(self.tokenize(record.normd_message))
            for word, count in counts.items():
                if word not in self.vocab:
                    self.vocab.add(word)
                if word not in self.attr_counts[c]:
                    self.attr_counts[c][word] = 0
                self.attr_counts[c][word] += count

            for attr in CUSTOM_ATTRS:
                v = getattr(record, attr)
                if round_value := self.round_values.get(attr):
                    v = round(v, round_value)
                attr = '_' + attr + '_' + str(v)
                if attr not in self.attr_counts[c]:
                    self.attr_counts[c][attr] = 0
                self.attr_counts[c][attr] += 1

            if record.category not in self.classes_:
                self.classes_[record.category] = record.category+1

    def predict(self, data: list[Message]) -> list[CLASS]:
        result = []
        for record in data:
            counts = self.get_word_counts(self.tokenize(record.normd_message))
            spam_score = 0
            ham_score = 0
            for word, _ in counts.items():
                if word not in self.vocab:
                    continue

                # add Laplace smoothing
                # apparitions of that word in spam vocab / number of words in spam
                log_w_given_spam = math.log((self.attr_counts['spam'].get(
                    word, 0) + 1) / (self.num_messages['spam'] + len(self.vocab)))
                log_w_given_ham = math.log((self.attr_counts['ham'].get(
                    word, 0) + 1) / (self.num_messages['ham'] + len(self.vocab)))
                spam_score += log_w_given_spam
                ham_score += log_w_given_ham

            for attr in CUSTOM_ATTRS:
                v = getattr(record, attr)
                if round_value := self.round_values.get(attr):
                    v = round(v, round_value)
                attr = '_' + attr + '_' + str(v)
                log_attr_given_spam = math.log((self.attr_counts['spam'].get(attr, 0) + 1) / (self.num_messages['spam'] + len(self.vocab)))
                log_attr_given_ham = math.log((self.attr_counts['ham'].get(attr, 0) + 1) / (self.num_messages['ham'] + len(self.vocab)))
                spam_score += log_attr_given_spam
                ham_score += log_attr_given_ham

            spam_score += self.log_class_priors['spam']
            ham_score += self.log_class_priors['ham']
            if spam_score > ham_score:
                result.append(1)
            else:
                result.append(0)
        return result

class RandomForest:
    "Random forest using the Bayes classification algorithm to detect if a message is a scam"

    def __init__(self, ntree: int, test_percent: float, round_values: RoundValueType):
        self.ntree = ntree
        self.test_percent = test_percent
        self.round_values = round_values
        self.trees: list[SpamDetector] = []
        self.vocab = set()
        self.tests: list[list[Message]] = []
        self.classes_: dict[int, int] = {} # map class ID to index

    def fit(self, data: list[Message], y_values: Optional[list[CLASS]]=None):
        "Train the model for a given list of messages"
        # calculate quantity of rows used to train each tree
        learning_amount = round((1-self.test_percent) * len(data))
        # reset variables
        self.vocab.clear()
        self.tests.clear()
        self.classes_.clear()
        # init trees
        self.trees = [SpamDetector(self.round_values) for _ in range(self.ntree)]
        # train trees
        for tree in self.trees:
            learning = random.sample(data, learning_amount)
            tree.fit(learning)
            self.vocab |= tree.vocab
            self.classes_ |= tree.classes_
            self.tests.append([x for x in data if x not in learning])
        return self

    def set_params(self, ntree: int, test_percent: float, round_values: RoundValueType):
        "Edit the model parameters"
        self.ntree = ntree
        self.test_percent = test_percent
        self.round_values = round_values
        return self

    def get_params(self, deep: bool = True): # pylint: disable=unused-argument
        "Get the current model parameters"
        return {
            'ntree': self.ntree,
            'test_percent': self.test_percent,
            'round_values': self.round_values,
        }

    def save(self):
        pickle.dump(self, open(os.path.dirname(__file__)+"/data/bayes_model.pkl", 'wb'))

    def predict(self, x_dataset: list[Message]) -> list[CLASS]:
        "Predict the class index for each given message"
        result = [0 for _ in range(len(x_dataset))]
        for tree in self.trees:
            for i, x in enumerate(tree.predict(x_dataset)):
                result[i] += x/len(self.trees)
        return [round(x) for x in result]

    def get_external_accuracy(self, data: list[Message]) -> float:
        "Get the model accuracy based on a given dataset"
        pred = self.predict(data)
        return sum(1 for i in range(len(pred)) if pred[i] == data[i].category) / float(len(pred))

    def get_classes(self, record: Message) -> dict[str, float]:
        "Get the probability of each class for a given message"
        result = [0, 0]
        for tree in self.trees:
            pred = tree.predict([record])[0]
            result[pred] += 1/len(self.trees)
        # return list(map(lambda x: round(x, 5), result))
        return {self.classes_[i]: round(x, 5) for i,x in enumerate(result)}
