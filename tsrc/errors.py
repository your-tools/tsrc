""" Custom exceptions """

from path import Path

DOC_URL = "https://supertanker.github.io/tsrc/ref/formats/"


class Error(Exception):
    """ Base class for our own errors

    """
    def __init__(self, *args):
        super().__init__(self, *args)
        self.message = " ".join(str(x) for x in args)

    def __str__(self) -> str:
        return self.message


class InvalidConfig(Error):
    def __init__(self, config_path: Path, details: str) -> None:
        self.config_path = config_path
        self.details = details
        super().__init__(self.detailed_message)

    @property
    def detailed_message(self) -> str:
        res = "%s: %s" % (self.config_path, self.details)
        res += "\n"
        res += "See %s for details" % DOC_URL
        return res

    def __str__(self) -> str:
        return self.detailed_message
