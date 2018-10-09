""" Repo value object """

import attr
from typing import Optional, List  # noqa


@attr.s(frozen=True)
class Remote:
    name = attr.ib()  # type: str
    url = attr.ib()   # type: str


@attr.s(frozen=True)
class Repo():
    src = attr.ib()  # type: str
    branch = attr.ib(default="master")  # type: Optional[str]
    sha1 = attr.ib(default=None)  # type: Optional[str]
    tag = attr.ib(default=None)   # type: Optional[str]
    shallow = attr.ib(default=None)  # type: Optional[bool]

    remotes = attr.ib(default=list())  # type: List[Remote]

    @property
    def clone_url(self) -> str:
        assert self.remotes
        return self.remotes[0].url
