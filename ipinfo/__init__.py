from .handler import Handler


def getHandler(access_token=None, **kwargs):
    """Create and return Handler object."""
    return Handler(access_token, **kwargs)
