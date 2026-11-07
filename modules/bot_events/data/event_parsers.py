import datetime
import json


def parse_json_column(value: object, column_name: str, expected_type: type) -> object:
    "Decode a JSON column and ensure it has the expected top-level type"
    if isinstance(value, (str, bytes, bytearray)):
        value = json.loads(value)
    if not isinstance(value, expected_type):
        raise TypeError(
            f"Expected {column_name} to contain {expected_type.__name__}, "
            f"got {type(value).__name__}"
        )
    return value


def ensure_utc_datetime(value: datetime.date | datetime.datetime) -> datetime.datetime:
    "Convert a SQL DATE or DATETIME value to a timezone-aware UTC datetime"
    if isinstance(value, datetime.datetime):
        return value.astimezone(datetime.UTC)
    return datetime.datetime.combine(value, datetime.time.min, tzinfo=datetime.UTC)
