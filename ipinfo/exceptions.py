"""
Exceptions thrown by the IPinfo service.
"""


class RequestQuotaExceededError(Exception):
    """Error indicating that users monthly request quota has been passed."""

    pass
