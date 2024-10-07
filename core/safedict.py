class SafeDict(dict):
    "Replaces missing keys with {key} so that format strings don't raise KeyError"

    def __missing__(self, key):
        return '{' + key + '}'
