"""
Abstract interface for caching IPinfo data.
"""

import abc
import six


@six.add_metaclass(abc.ABCMeta)
class CacheInterface():
    """Interface for using custom cache."""

    @abc.abstractmethod
    def __contains__(self, key):
        pass

    @abc.abstractmethod
    def __setitem__(self, key, value):
        pass

    @abc.abstractmethod
    def __getitem__(self, key):
        pass
