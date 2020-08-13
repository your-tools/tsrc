""" Entry point for tsrc version """

import tsrc


def version() -> None:
    """ show version number """
    print("tsrc version", tsrc.__version__)
