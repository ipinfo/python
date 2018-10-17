"""
A Memcached-based cache backend implementation.
"""

import re
from .interface import CacheInterface


class Memcached(CacheInterface):
    """
    Memcached-based cache backend.

    Memcached implements an LRU cache eviction policy internally, so we don't need to implement anything here.
    """

    def __init__(self, servers, **kwargs):
        if isinstance(servers, str):
            servers = re.split('[;,]', servers)

        # We import here to prevent a crash in case the client doesn't have python-memcached installed.
        import memcache
        self.cache = memcache.Client(servers, **kwargs)

    def __contains__(self, key):
        return self.cache.get(key) is not None

    def __setitem__(self, key, value):
        return self.cache.set(key, value)

    def __getitem__(self, key):
        return self.cache.get(key)
