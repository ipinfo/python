from .handler import Handler
from .handler_async import AsyncHandler


def getHandler(access_token=None, **kwargs):
    """Create and return Handler object."""
    return Handler(access_token, **kwargs)


def getHandlerAsync(access_token=None, **kwargs):
    """Create an return an asynchronous Handler object."""
    return AsyncHandler(access_token, **kwargs)
