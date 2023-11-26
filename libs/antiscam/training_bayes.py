import itertools
from random import shuffle

from sklearn.model_selection import RandomizedSearchCV

from . import Message, RandomForest
from .bayes import RoundValueType


async def get_roundvalues_combinations(values_range: range) -> list[RoundValueType]:
    "Get all possible combinations of round values"
    keys = ('max_frequency', 'caps_percentage', 'avg_word_len')
    values = [list(values_range) for _ in range(len(keys))]
    return [dict(zip(keys, v)) for v in itertools.product(*values)]

async def train_model(data: list[Message], quick_train: bool=False):
    "Train a new model with the given data"
    model = RandomForest(ntree=100, test_percent=0.2, round_values={'max_frequency': 3, 'caps_percentage': 1, 'avg_word_len': 2})
    param_grid = {
        'ntree': [50, 100, 200, 300, 400],
        'test_percent': [.15, .2, .25, .3, .35],
        'round_values': await get_roundvalues_combinations(range(4))
    }
    shuffle(data)
    y_values = [msg.category for msg in data]
    # Start the training
    search = RandomizedSearchCV(model, param_grid,
                                scoring="balanced_accuracy",
                                n_iter=5 if quick_train else 40,
                                n_jobs=-1,
                                error_score='raise'
                                )
    search.fit(data, y_values)
    print(f"{search.best_params_ = }")
    best_model = RandomForest(**search.best_params_)
    best_model.fit(data)
    return best_model
