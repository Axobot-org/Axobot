from core.type_utils import AnyStrDict


class SafeDict(AnyStrDict):
    "Replaces missing keys with {key} so that format strings don't raise KeyError"

    def __missing__(self, key: str) -> str:
        return '{' + key + '}'
