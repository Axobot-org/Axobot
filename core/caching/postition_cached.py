from typing import Any

from asyncache import cached
from cachetools import TTLCache


def position_cached(cache: TTLCache[Any, Any], *, key: int):
    """
    Decorator to cache the position of a given key in a TTLCache.

    Args:
        cache (TTLCache): The cache to use for storing positions.
        key (int): The key whose position is to be cached.

    Returns:
        function: The decorated function that caches the position.
    """
    return cached(cache, key=lambda *args, **kwargs: [*args, *kwargs][key])
