from .handler_lite import HandlerLite
from .handler_lite_async import AsyncHandlerLite
from .handler import Handler
from .handler_async import AsyncHandler
from .handler_core import HandlerCore
from .handler_core_async import AsyncHandlerCore
from .handler_plus import HandlerPlus
from .handler_plus_async import AsyncHandlerPlus


def getHandler(access_token=None, **kwargs):
    """Create and return Handler object."""
    return Handler(access_token, **kwargs)


def getHandlerLite(access_token=None, **kwargs):
    """Create and return HandlerLite object."""
    return HandlerLite(access_token, **kwargs)


def getHandlerCore(access_token=None, **kwargs):
    """Create and return HandlerCore object."""
    return HandlerCore(access_token, **kwargs)


def getHandlerPlus(access_token=None, **kwargs):
    """Create and return HandlerPlus object."""
    return HandlerPlus(access_token, **kwargs)


def getHandlerAsync(access_token=None, **kwargs):
    """Create an return an asynchronous Handler object."""
    return AsyncHandler(access_token, **kwargs)


def getHandlerAsyncLite(access_token=None, **kwargs):
    """Create and return asynchronous HandlerLite object."""
    return AsyncHandlerLite(access_token, **kwargs)


def getHandlerAsyncCore(access_token=None, **kwargs):
    """Create and return asynchronous HandlerCore object."""
    return AsyncHandlerCore(access_token, **kwargs)


def getHandlerAsyncPlus(access_token=None, **kwargs):
    """Create and return asynchronous HandlerPlus object."""
    return AsyncHandlerPlus(access_token, **kwargs)
