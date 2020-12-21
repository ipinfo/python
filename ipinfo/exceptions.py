"""
Exceptions thrown by the IPinfo service.
"""


class RequestQuotaExceededError(Exception):
    """Error indicating that users monthly request quota has been passed."""

    pass


class TimeoutExceededError(Exception):
    """Error indicating that some timeout has been exceeded."""

    pass
