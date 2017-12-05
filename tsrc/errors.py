""" Custom exceptions """


DOC_URL = "https://supertanker.github.io/tsrc/ref/formats/"


class Error(Exception):
    """ Base class for our own errors

    """
    def __init__(self, *args):
        super().__init__(self, *args)
        self.message = " ".join(str(x) for x in args)

    def __str__(self):
        return self.message


class InvalidConfig(Error):
    def __init__(self, path, details):
        self.path = path
        self.details = details
        super().__init__(self.detailed_message)

    @property
    def detailed_message(self):
        res = "%s: %s" % (self.path, self.details)
        res += "\n"
        res += "See %s for details" % DOC_URL
        return res

    def __str__(self):
        return self.detailed_message
