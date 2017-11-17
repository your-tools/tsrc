""" Repo value object """

import attr


# pylint: disable=too-few-public-methods
@attr.s(frozen=True)
class Repo():
    src = attr.ib()
    url = attr.ib()
    branch = attr.ib(default="master")
    sha1 = attr.ib(default=None)
    tag = attr.ib(default=None)
    shallow = attr.ib(default=None)
