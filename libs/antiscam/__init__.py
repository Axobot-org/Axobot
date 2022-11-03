import csv
import os
import pickle
from typing import Union, Optional

from .classes import Message, PredictionResult
from .bayes import RandomForest, SpamDetector

class AntiScamAgent:
    """Class taking care or everything"""

    def __init__(self):
        self.categories = {
            0: 'pending',
            1: 'harmless',
            2: 'scam',
            3: 'insults',
            4: 'raid',
            5: 'spam'
        }
        self.model = self.get_model()
        # map of <domain_name, is_safe>
        self.websites_list: Optional[dict[str, bool]] = None

    def fetch_websites_locally(self, filename: Optional[str] = None):
        "Fetch the websites list from a local CSV file, if possible"
        filepath = filename if filename else os.path.dirname(__file__) + "/data/base_websites.csv"
        self.websites_list = {}
        with open(filepath, 'r', encoding='utf-8') as csv_file:
            spamreader = csv.reader(csv_file)
            for row in spamreader:
                self.websites_list[row[0]] = row[1] == '1'

    def save_websites_locally(self, data: dict[str, bool], filename: Optional[str] = None):
        "Save the websites list to a local CSV file"
        filepath = filename if filename else os.path.dirname(__file__) + "/data/base_websites.csv"
        with open(filepath, 'w', encoding='utf-8') as csv_file:
            spamwriter = csv.writer(csv_file)
            for key, value in data.items():
                spamwriter.writerow([key, value])
        self.websites_list = data

    def get_category_id(self, name: str):
        "Get a category ID from its name (like a reversed map)"
        for key, value in self.categories.items():
            if value == name:
                return key

    def get_model(self) -> RandomForest:
        "Get back our trained bayes model"
        class CustomUnpickler(pickle.Unpickler):
            "Custom unpickler to make sure to find our classes"
            def find_class(self, module, name):
                if name == 'RandomForest':
                    return RandomForest
                if name == 'SpamDetector':
                    return SpamDetector
                if module == 'classes' and name == 'Message':
                    return Message
                return super().find_class(module, name)
        with open(os.path.dirname(__file__)+"/data/bayes_model.pkl", 'rb') as raw:
            return CustomUnpickler(raw).load()

    def predict_bot(self, message: Union[Message, str]):
        "Try to predict the dangerousity of a message"
        if isinstance(message, str):
            dataset = Message.from_raw(message, 0)
        elif isinstance(message, Message):
            dataset = message
        else:
            raise TypeError("'message' should be either a string or a Message")

        prediction = self.model.get_classes(dataset)

        return PredictionResult(prediction.values(), prediction.keys())
