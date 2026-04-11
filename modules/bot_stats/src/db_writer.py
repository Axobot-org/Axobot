from collections.abc import Sequence
from datetime import datetime
from typing import Any, NamedTuple

from core.database import DatabaseQueryHandler


class StatRow(NamedTuple):
    "A single stat data point ready for insertion into the stats database."
    variable: str
    value: int | float
    type_flag: int  # 0 = integer, 1 = float
    unit: str
    is_sum: bool


async def write_stats_batch(
    db: DatabaseQueryHandler,
    entity_id: int,
    now: datetime,
    rows: Sequence[StatRow],
) -> None:
    "Insert all stat rows in a single batch INSERT into the zbot table."
    if not rows:
        return
    placeholders = ", ".join(["(%s, %s, %s, %s, %s, %s, %s)"] * len(rows))
    query = (
        "INSERT INTO `zbot` (`date`, `variable`, `value`, `type`, `unit`, `is_sum`, `entity_id`) VALUES "
        + placeholders
    )
    args: list[Any] = []
    for row in rows:
        args.extend([now, row.variable, row.value, row.type_flag, row.unit, row.is_sum, entity_id])
    async with db.write(query, tuple(args)):
        pass
