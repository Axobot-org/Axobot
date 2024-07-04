
from math import ceil, floor

async def get_level_from_xp_global(xp: int) -> int:
    "Returns the level from the given xp"
    approx_level = 1 + pow(xp, 13/20) * 7/125
    return floor(round(approx_level, 3))

async def get_xp_from_level_global(level: int) -> int:
    "Returns the xp needed to reach the given level"
    return ceil(pow((level-1) * 125/7, 20/13))

async def get_level_from_xp_mee6(xp: int) -> int:
    "Returns the level from the given xp (MEE6 system)"
    lvl = 0
    lvl_xp = 0
    while xp >= lvl_xp:
        lvl_xp += 5*pow(lvl, 2) + 50*lvl + 100
        lvl += 1
    return lvl - 1

async def get_xp_from_level_mee6(level: int) -> int:
    "Returns the xp needed to reach the given level (MEE6 system)"
    approx_level = 5/3 * pow(level, 3) + 22.5 * pow(level, 2) + 151515/1998 * level
    return floor(round(approx_level, 3))
