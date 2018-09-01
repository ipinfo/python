class Details:

    def __init__(self, details):
        self.details = details

    def __getattr__(self, attr):
        if attr in self.details:
            return self.details[attr]
        else:
            raise AttributeError('{attr} is not a valid attribute of Details'.format(attr))

    @property
    def all(self):
        return self.details
