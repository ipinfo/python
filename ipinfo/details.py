"""
Details returned by the IPinfo service.
"""


class Details:
    """Encapsulates data for single IP address."""

    def __init__(self, details):
        """Initialize by settings `details` attribute."""
        self.details = details

    def __getattr__(self, attr):
        """Return attribute if it exists in details array, else return error."""
        if attr in self.details:
            return self.details[attr]
        else:
            raise AttributeError(
                "{} is not a valid attribute of Details".format(attr)
            )

    @property
    def all(self):
        """Return all details as dict."""
        return self.details
