from .handler_lite import HandlerLite
from .handler_lite_async import AsyncHandlerLite
from .handler import Handler
from .handler_async import AsyncHandler


def getHandler(access_token=None, **kwargs):
    """Create and return Handler object."""
    return Handler(access_token, **kwargs)


def getHandlerLite(access_token=None, **kwargs):
    """Create and return HandlerLite object."""
    return HandlerLite(access_token, **kwargs)


def getHandlerAsync(access_token=None, **kwargs):
    """Create an return an asynchronous Handler object."""
    return AsyncHandler(access_token, **kwargs)


def getHandlerAsyncLite(access_token=None, **kwargs):
    """Create and return asynchronous HandlerLite object."""
    return AsyncHandlerLite(access_token, **kwargs)
