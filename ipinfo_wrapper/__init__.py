from .handler import Handler

def getHandler(access_token=None, **kwargs):
    return Handler(access_token, **kwargs)
