from typing import Literal, TypedDict

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn import model_selection
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import f1_score
from sklearn.model_selection import RandomizedSearchCV


class RecordedRow(TypedDict):
    "Represents a data row as used to train our model"
    class_id: int
    class_label: str
    message: str
    contains_everyone: bool
    mentions_count: int
    url_score: int
    max_frequency: float
    punctuation_count: int
    caps_percentage: float
    avg_word_len: float

class ModelParameters(TypedDict):
    "Represents the parameters of our model"
    num_leaves: int
    min_data_in_leaf: int
    max_depth: int
    learning_rate: float
    bagging_freq: int
    bagging_fraction: float
    reg_alpha: float
    reg_lambda: float
    min_split_gain: float
    min_child_weight: float
    min_child_samples: int
    subsample: float
    boosting: Literal["gbdt", "dart", "goss", "rf"]

async def extract_tfidf(dataframe: pd.DataFrame):
    "Apply the Term frequency inverse document frequency algorithm"
    # Extract the list of messages only
    messages_df = dataframe['message']
    # Create the vector from the messages
    tfidf_model = TfidfVectorizer()
    tfidf_vec = tfidf_model.fit_transform(messages_df)
    # Create a new dataframe from the vector
    tfidf_data = pd.DataFrame(tfidf_vec.toarray())
    # Add nearly every column to the new dataframe
    for column in dataframe.columns:
        if column not in {'class_label', 'message'}:
            tfidf_data[column] = dataframe[column]
    return tfidf_data

async def split_test_train(tfidf_data: pd.DataFrame) -> tuple[list, list, list, list]:
    "Split the data into a training and test set"
    # separating columns
    cut = round(len(tfidf_data)*0.8)
    df_train = tfidf_data.iloc[:cut]
    # create X (input) and Y (output) training datasets
    y_data = df_train['class']
    x_data = df_train.drop('class', axis=1)
    # splitting training data into train and validation using sklearn
    # The split ratio for the validation set is 20% of the training data.
    return model_selection.train_test_split(x_data, y_data, test_size=.2, random_state=42)

async def find_best_params(x_train: list, y_train: list) -> ModelParameters:
    "Find the best parameters for our model"
    lgbmodel_bst = lgb.LGBMClassifier(n_estimators=200, num_leaves=40, importance_type='gain')
    param_grid = {
        'num_leaves': list(range(8, 92, 4)),
        'min_data_in_leaf': [10, 20, 40, 60, 80, 100],
        'max_depth': [5, 6, 7, 8, 12, 16, 20, -1],
        'learning_rate': [0.1, 0.05, 0.01, 0.005],
        'bagging_freq': [3, 4, 5, 6, 7],
        'bagging_fraction': np.linspace(0.6, 0.95, 10),
        'reg_alpha': np.linspace(0.1, 0.95, 10),
        'reg_lambda': np.linspace(0.1, 0.95, 10),
        "min_split_gain": [0.0, 0.1, 0.01],
        "min_child_weight": [0.001, 0.01, 0.1, 0.001],
        "min_child_samples": [20, 25, 30, 35],
        "subsample": [1.0, 0.5, 0.8],
        "boosting": ["gbdt", "dart", "rf"]
    }
    model = RandomizedSearchCV(lgbmodel_bst, param_grid, random_state=1, n_iter=30, n_jobs=-1)
    search = model.fit(x_train, y_train)
    return search.best_params_

async def train_best_model(params: ModelParameters, x_train: list, y_train: list):
    "Train a LGBMClassifier model from the given parameters"
    best_model = lgb.LGBMClassifier(**params, random_state=1, importance_type='gain')
    best_model.fit(x_train, y_train)
    return best_model

async def test_model(model: lgb.LGBMClassifier, x_test: list, y_test: list):
    "Test the given model with the given data"
    y_pred = model.predict(x_test)
    score_by_class: tuple[float, float, float] = f1_score(y_test, y_pred, average=None)
    avg_score: float = f1_score(y_test, y_pred, average='weighted')
    return score_by_class, avg_score

async def train_model(rows: list[RecordedRow]):
    "Launch every required function to train a new model based on given data"
    # Convert the list of rows to a pandas dataframe
    df = pd.DataFrame(rows)
    # Add the length of each message as a new column
    df['length'] = df['message'].apply(len)
    # Apply TFIDF
    tfidf_data = await extract_tfidf(df)
    # Collect training data
    x_train, x_test, y_train, y_test = await split_test_train(tfidf_data)
    # Find the best parameters for our model (this may take a looooong time)
    best_params = await find_best_params(x_train, y_train)
    # And then apply them to our model
    best_model = await train_best_model(best_params, x_test, y_test)
    return best_model
