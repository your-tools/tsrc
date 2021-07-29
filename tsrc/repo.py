""" Repo objects. """
from typing import List, Optional

import attr


@attr.s(frozen=True)
class Remote:
    name: str = attr.ib()
    url: str = attr.ib()


@attr.s(frozen=True)
class Repo:
    dest: str = attr.ib()
    # Note: a repo has at least one remote called 'origin' by default -
    # other remotes may be configured explicitly in the manifest file.
    remotes: List[Remote] = attr.ib()
    branch: str = attr.ib(default="master")
    sha1: Optional[str] = attr.ib(default=None)
    tag: Optional[str] = attr.ib(default=None)
    shallow: bool = attr.ib(default=False)

    @property
    def clone_url(self) -> str:
        assert self.remotes
        return self.remotes[0].url
