""" Repo objects. """
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class Remote:
    name: str
    url: str


@dataclass(frozen=True)
class Repo:
    dest: str
    # Note: a repo has at least one remote called 'origin' by default -
    # other remotes may be configured explicitly in the manifest file.
    remotes: List[Remote]
    branch: str = "master"
    sha1: Optional[str] = None
    tag: Optional[str] = None
    shallow: bool = False
    ignore_submodules: bool = False

    @property
    def clone_url(self) -> str:
        assert self.remotes
        return self.remotes[0].url
