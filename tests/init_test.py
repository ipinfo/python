import ipinfo
from ipinfo.handler import Handler


def test_get_handler():
    handler = ipinfo.getHandler()
    assert isinstance(handler, Handler)
