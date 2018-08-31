from .interface import CacheInterface
import cachetools

class DefaultCache(CacheInterface):

    def __init__(self, maxsize, ttl, **cache_options):
        self.cache = cachetools.TTLCache(maxsize, ttl, **cache_options)

    def __contains__(self, key):
        return self.cache.__contains__(key)

    def __setitem__(self, key, value):
        return self.cache.__setitem__(key, value)

    def __getitem__(self, key):
        return self.cache.__getitem__(key)
