""" Repo objects. """

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cli_ui as ui

from tsrc.manifest_common_data import ManifestsTypeOfData, get_main_color


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
    # Q: how to setup Repo with empty branch?
    # A: branch = None, keep_branch = True
    # this is necessary when dumping to Manifest, so we will know
    # when to set SHA1 for sure
    branch: Optional[str] = None
    keep_branch: bool = False
    is_default_branch: bool = False
    # orig_branch should be set when Repo dataclass is created
    # in order to keep original branch present, as after
    # update(), branch may be changed loosing its original value.
    # this is important when syncing using 'ref'
    # see 'test/cli/test_sync_to_ref.py' for even more details
    orig_branch: Optional[str] = None
    sha1: Optional[str] = None
    tag: Optional[str] = None
    shallow: bool = False
    ignore_submodules: bool = False

    def __post_init__(self) -> None:
        if not self.branch and self.keep_branch is False:
            object.__setattr__(self, "branch", "master")
            object.__setattr__(self, "is_default_branch", True)

    @property
    def clone_url(self) -> str:
        assert self.remotes
        return self.remotes[0].url

    """copy from 'git.py'"""

    def describe_to_tokens(
        self, ljust: int = 0, tod: ManifestsTypeOfData = ManifestsTypeOfData.LOCAL
    ) -> Tuple[List[ui.Token], List[ui.Token]]:
        """returns:
        1st: is properly left-align: for print
        2nd: is NOT align: for 1:1 comparsion"""
        cb = ui.green  # color (for) branch
        cs = ui.red  # color (for) SHA1
        ct = ui.brown  # color (for) tag
        if tod == ManifestsTypeOfData.DEEP or tod == ManifestsTypeOfData.FUTURE:
            cb = cs = get_main_color(tod)

        res: List[ui.Token] = []
        able: List[ui.Token] = []
        first_ljust = ljust
        if self.tag:
            first_ljust = 0
        if self.branch and (
            self.is_default_branch is False or (not self.sha1 and not self.tag)
        ):
            res += [cb, self.branch.ljust(first_ljust), ui.reset]
            able += [ui.green, self.branch, ui.reset]
            if first_ljust == 0:
                ljust -= len(self.branch) + 1
        elif self.sha1:
            sha1 = self.sha1[:7]  # artificially shorten
            res += [cs, sha1.ljust(first_ljust), ui.reset]
            able += [ui.red, sha1, ui.reset]
            if first_ljust == 0:
                ljust -= len(sha1) + 1
        if self.tag:
            # we have to compensate for len("on ")
            res += [ct, "on", self.tag.ljust(ljust - 3), ui.reset]
            able += [ui.brown, "on", self.tag, ui.reset]
        return res, able

    def len_of_describe(self) -> int:
        len_: int = 0
        if self.branch and (
            self.is_default_branch is False or (not self.sha1 and not self.tag)
        ):
            len_ += len(self.branch)
        elif self.sha1:
            sha1 = self.sha1[:7]  # artificially shorten
            len_ += len(sha1)
        if self.tag:
            len_ += len(self.tag) + 4  # " on "
        return len_
