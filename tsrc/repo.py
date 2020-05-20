""" Repo value object """

import attr
from typing import Optional, List  # noqa


@attr.s(frozen=True)
class Remote:
    name = attr.ib()  # type: str
    url = attr.ib()  # type: str


@attr.s(frozen=True)
class Copy:
    repo = attr.ib()  # type: str
    src = attr.ib()  # type: str
    dest = attr.ib()  # type: str


@attr.s(frozen=True)
class Repo:
    dest = attr.ib()  # type: str
    remotes = attr.ib()  # type: List[Remote]
    branch = attr.ib(default="master")  # type: str
    sha1 = attr.ib(default=None)  # type: Optional[str]
    tag = attr.ib(default=None)  # type: Optional[str]
    shallow = attr.ib(default=False)  # type: bool

    @property
    def clone_url(self) -> str:
        assert self.remotes
        return self.remotes[0].url
