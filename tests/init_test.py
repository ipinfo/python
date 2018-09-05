import ipinfo_wrapper
from ipinfo_wrapper.handler import Handler


def test_get_handler():
    handler = ipinfo_wrapper.getHandler()
    assert(isinstance(handler, Handler))
