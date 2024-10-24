""" Repo objects. """

from dataclasses import dataclass
from enum import Enum, unique
from pathlib import Path
from typing import List, Optional, Tuple

import cli_ui as ui

from tsrc.manifest_common_data import ManifestsTypeOfData, mtod_get_main_color


@unique
class DescribeToTokens(Enum):
    NONE = 0
    BRANCH = 1
    SHA1 = 2
    TAG = 3
    MISSING_REMOTES = 4


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
    # only used by RepoGrabber
    _grabbed_from_path: Optional[Path] = None

    def __post_init__(self) -> None:
        if not self.branch and self.keep_branch is False:
            object.__setattr__(self, "branch", "master")
            object.__setattr__(self, "is_default_branch", True)

    def rename_dest(self, new_dest: str) -> None:
        object.__setattr__(self, "dest", new_dest)

    @property
    def clone_url(self) -> str:
        assert self.remotes
        return self.remotes[0].url

    """copy from 'git.py'"""

    def describe_to_tokens(
        self, ljust: int = 0, mtod: ManifestsTypeOfData = ManifestsTypeOfData.LOCAL
    ) -> Tuple[List[ui.Token], List[ui.Token]]:
        """returns:
        1st: is properly left-align: for print
        2nd: is NOT align: for 1:1 comparsion"""

        # 1st caluclate total length of all elements
        sha1: str = ""
        if self.sha1:
            sha1 = self.sha1[:7]  # artificially shorten

        present_dtt: List[DescribeToTokens] = []
        if self.branch and (
            self.is_default_branch is False or (not self.sha1 and not self.tag)
        ):
            present_dtt.append(DescribeToTokens.BRANCH)
        elif self.sha1:
            present_dtt.append(DescribeToTokens.SHA1)
        if self.tag:
            present_dtt.append(DescribeToTokens.TAG)
        if not self.remotes:
            if mtod == ManifestsTypeOfData.DEEP or mtod == ManifestsTypeOfData.FUTURE:
                present_dtt.append(DescribeToTokens.MISSING_REMOTES)
        if not present_dtt:
            present_dtt.append(DescribeToTokens.NONE)

        # return res, able
        return self._describe_to_token_output(present_dtt, ljust, mtod, sha1)

    def _describe_to_token_output(
        self,
        present_dtt: List[DescribeToTokens],
        ljust: int,
        mtod: ManifestsTypeOfData,
        sha1: str,
    ) -> Tuple[ui.Token, ui.Token]:
        cb = ui.green  # color (for) branch
        cs = ui.red  # color (for) SHA1
        ct = ui.brown  # color (for) tag
        if mtod == ManifestsTypeOfData.DEEP or mtod == ManifestsTypeOfData.FUTURE:
            cb = cs = mtod_get_main_color(mtod)
        res: List[ui.Token] = []
        able: List[ui.Token] = []

        # 2nd detect last element for 'ljust' to apply'
        last_element: DescribeToTokens = present_dtt[-1]

        # 3rd fill the 'res' and 'able'
        for e in present_dtt:
            this_ljust: int = 0
            if e == last_element:
                this_ljust = ljust
            if e == DescribeToTokens.BRANCH and self.branch:
                res += [cb, self.branch.ljust(this_ljust), ui.reset]
                able += [ui.green, self.branch, ui.reset]
                ljust -= len(self.branch) + 1
            elif e == DescribeToTokens.SHA1:
                res += [cs, sha1.ljust(this_ljust), ui.reset]
                able += [ui.red, sha1, ui.reset]
                ljust -= len(sha1) + 1
            elif e == DescribeToTokens.TAG and self.tag:
                res += [ct, "on", self.tag.ljust(this_ljust - 3), ui.reset]
                able += [ui.brown, "on", self.tag, ui.reset]
                ljust -= len(self.tag) + 1 + 2 + 1  # + " on "
            elif e == DescribeToTokens.MISSING_REMOTES:
                res += [ui.red, "(missing remote)".ljust(this_ljust), ui.reset]
                able += [ui.red, "(missing remote)", ui.reset]
                ljust -= 16 + 1  # len of "(missing remote) "
            else:  # DescribeToTokens.NONE:
                res += [" ".ljust(this_ljust)]
                able += [" "]
        return res, able

    def len_of_describe(
        self, mtod: ManifestsTypeOfData = ManifestsTypeOfData.LOCAL
    ) -> int:
        len_: int = 0
        if self.branch and (
            self.is_default_branch is False or (not self.sha1 and not self.tag)
        ):
            len_ += len(self.branch) + 1
        elif self.sha1:
            sha1 = self.sha1[:7]  # artificially shorten
            len_ += len(sha1) + 1
        if self.tag:
            len_ += len(self.tag) + 4  # " on "
        if not self.remotes:
            if mtod == ManifestsTypeOfData.DEEP or mtod == ManifestsTypeOfData.FUTURE:
                len_ += 16 + 1
        if len_ > 0:
            len_ -= 1
        return len_
