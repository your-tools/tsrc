""" Repo value object """

import attr


# pylint: disable=too-few-public-methods
@attr.s(frozen=True)
class Repo():
    src = attr.ib()
    url = attr.ib()
    branch = attr.ib(default="master")
    fixed_ref = attr.ib(default=None)
