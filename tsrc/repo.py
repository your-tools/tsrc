""" Repo objects. """

from dataclasses import dataclass
from enum import Enum, unique
from typing import List, Optional, Tuple

import cli_ui as ui


@unique
class TypeOfDescribeBranch(Enum):
    COMMON = 1
    DM = 2
    FM = 3


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

    """copy from 'git.py'"""

    def describe_branch(
        self, ljust: int = 0, tod: TypeOfDescribeBranch = TypeOfDescribeBranch.COMMON
    ) -> Tuple[List[ui.Token], List[ui.Token]]:
        """returns:
        1st: is properly left-adjusted: for print
        2nd: is not: for 1:1 comparsion"""
        cb = ui.green  # color (for) branch
        cs = ui.red  # color (for) SHA1
        ct = ui.brown  # color (for) tag
        if tod == TypeOfDescribeBranch.DM:
            cb = cs = ui.purple
        if tod == TypeOfDescribeBranch.FM:
            cb = cs = ui.cyan

        res: List[ui.Token] = []
        able: List[ui.Token] = []
        first_ljust = ljust
        if self.tag:
            first_ljust = 0
        if self.branch:
            res += [cb, self.branch.ljust(first_ljust), ui.reset]
            able += [ui.green, self.branch, ui.reset]
            if first_ljust == 0:
                ljust -= len(self.branch) + 1
        elif self.sha1:
            res += [cs, self.sha1.ljust(first_ljust), ui.reset]
            able += [ui.red, self.sha1, ui.reset]
            if first_ljust == 0:
                ljust -= len(self.sha1) + 1
        if self.tag:
            # we have to compensate for len("on ")
            res += [ct, "on", self.tag.ljust(ljust - 3), ui.reset]
            able += [ui.brown, "on", self.tag, ui.reset]
        return res, able

    def len_of_describe_branch(self) -> int:
        len_: int = 0
        if self.branch:
            len_ += len(self.branch)
        elif self.sha1:
            len_ += len(self.sha1)
        if self.tag:
            len_ += len(self.tag) + 4  # " on "
        return len_
