""" Repo objects. """
from typing import List, Optional  # noqa

import attr


@attr.s(frozen=True)
class Repo:
    dest = attr.ib()  # type: str
    # Note: a repo has at least one remote called 'origin' by default -
    # other remotes may be configured explicitly in the manifest file.
    remotes = attr.ib()  # type: List[Remote]
    branch = attr.ib(default="master")  # type: str
    sha1 = attr.ib(default=None)  # type: Optional[str]
    tag = attr.ib(default=None)  # type: Optional[str]
    shallow = attr.ib(default=False)  # type: bool

    @property
    def clone_url(self) -> str:
        assert self.remotes
        return self.remotes[0].url


@attr.s(frozen=True)
class Remote:
    name = attr.ib()  # type: str
    url = attr.ib()  # type: str
