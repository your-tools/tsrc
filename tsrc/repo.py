""" Repo value object """

import attr
from typing import Optional  # noqa


@attr.s(frozen=True)
class Repo():
    src = attr.ib()  # type: str
    url = attr.ib()  # type: str
    branch = attr.ib(default="master")  # type: Optional[str]
    sha1 = attr.ib(default=None)  # type: Optional[str]
    tag = attr.ib(default=None)   # type: Optional[str]
    shallow = attr.ib(default=None)  # type: Optional[bool]
