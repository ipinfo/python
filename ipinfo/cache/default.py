"""
A default cache implementation that uses `cachetools` for an in-memory LRU cache.
"""

from .interface import CacheInterface
from cachetools import TTLCache

class DefaultCache(CacheInterface):
    """Default, in-memory cache."""

    def __init__(self, **cache_options):
        self.cache = TTLCache(**cache_options)

    def __contains__(self, key):
        return self.cache.__contains__(key)

    def __setitem__(self, key, value):
        return self.cache.__setitem__(key, value)

    def __getitem__(self, key):
        return self.cache.__getitem__(key)

    def __delitem__(self, key):
        return self.cache.__delitem__(key)
