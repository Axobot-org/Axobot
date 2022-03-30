import os
import pickle
from typing import Union

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
