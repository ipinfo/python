import abc

class CacheInterface(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def __contains__(self, key):
        pass

    @abc.abstractmethod
    def __setitem__(self, key, value):
        pass

    @abc.abstractmethod
    def __getitem__(self, key):
        pass
