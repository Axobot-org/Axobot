from json import load
from typing import TYPE_CHECKING
import os

if TYPE_CHECKING:
    from .converters import AllRepresentation

current_file_dir = os.path.dirname(__file__) #<-- absolute dir the script is in
abs_file_path = os.path.join(current_file_dir, "options_list.json")

with open(abs_file_path, "r", encoding="utf8") as json_file:
    options: dict[str, "AllRepresentation"] = load(json_file)
