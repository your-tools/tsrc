""" Common tools """


class Error(Exception):
    """ Base class for our own errors

    """
    def __init__(self, *args):
        super().__init__(self, *args)
        self.message = " ".join(str(x) for x in args)

    def __str__(self):
        return self.message
