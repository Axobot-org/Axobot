import random

ALPHA = "abcdefghijklmnopqr?.,;_!-stuvwxyzABCDEFGHIJKL1234567890MNOPQRSTUVWXYZ" * 2

def crypte(string: str):
    key = random.randint(1, 9)
    r = str(key)
    for c in string:
        if c not in ALPHA:
            r += c
        else:
            r += ALPHA[ALPHA.find(c) + key]

    return r


def uncrypte(string: str):
    if not string[0].isnumeric():
        raise ValueError
    key = int(string[0])
    r = str()
    string = string[1:]
    for c in string:
        if c not in ALPHA:
            r += c
        else:
            co = ALPHA.find(c) - key
            if co < 0:
                co += len(ALPHA)
            r += ALPHA[co]
    return r
