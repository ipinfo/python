import ipinfo
from ipinfo.handler import Handler
from ipinfo.handler_async import AsyncHandler


def test_get_handler():
    handler = ipinfo.getHandler()
    assert isinstance(handler, Handler)


def test_get_handler_async():
    handler = ipinfo.getHandlerAsync()
    assert isinstance(handler, AsyncHandler)
