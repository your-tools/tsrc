""" Repo objects. """

from dataclasses import dataclass
from enum import Enum, unique
from pathlib import Path
from typing import List, Optional, Tuple

import cli_ui as ui

from tsrc.git import GitBareStatus
from tsrc.manifest_common_data import ManifestsTypeOfData, mtod_get_main_color
from tsrc.utils import len_of_cli_ui


@unique
class DescribeToTokens(Enum):
    NONE = 0
    BRANCH = 1
    SHA1 = 2
    TAG = 3
    POSITION = 4  # ahead or behind HEAD
    MISSING_REMOTES = 5


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
    # sha1_full: Optional[str] = None
    tag: Optional[str] = None
    shallow: bool = False
    ignore_submodules: bool = False
    is_bare: bool = False
    # only used by RepoGrabber
    _grabbed_from_path: Optional[Path] = None
    # only for BareCloner class
    _bare_clone_path: Optional[Path] = None
    _bare_clone_mtod: Optional[ManifestsTypeOfData] = None
    _bare_clone_orig_dest: Optional[str] = None  # from what Repo.dest we have come
    _bare_clone_is_ok: bool = True  # for relaying info about failed bare clone

    def __post_init__(self) -> None:
        if not self.branch and self.keep_branch is False:
            object.__setattr__(self, "branch", "master")
            object.__setattr__(self, "is_default_branch", True)

    def _bare_clone_is_fail(self) -> None:
        object.__setattr__(self, "_bare_clone_is_ok", False)

    def rename_dest(self, new_dest: str) -> None:
        object.__setattr__(self, "dest", new_dest)

    @property
    def clone_url(self) -> str:
        assert self.remotes
        return self.remotes[0].url

    def describe_to_tokens(
        self,
        ljust: int = 0,
        mtod: ManifestsTypeOfData = ManifestsTypeOfData.LOCAL,
        bare_dm_status: Optional[GitBareStatus] = None,
    ) -> Tuple[List[ui.Token], List[ui.Token]]:
        """returns:
        1st list: is properly left-align for print
        2nd list: is NOT align. it is for 1:1 comparsion"""

        sha1: str = ""
        if self.sha1:
            sha1 = self.sha1[:7]  # artificially shorten

        # keep all elements in this list and also
        # keep order of checking the elements
        present_dtt: List[DescribeToTokens] = []
        if self.branch and (
            self.is_default_branch is False or (not self.sha1 and not self.tag)
        ):
            present_dtt.append(DescribeToTokens.BRANCH)
        elif self.sha1:
            present_dtt.append(DescribeToTokens.SHA1)
        if self.tag:
            present_dtt.append(DescribeToTokens.TAG)

        if self.sha1:
            if DescribeToTokens.SHA1 not in present_dtt:
                # obtain 'describe_position' for this flag
                present_dtt.append(DescribeToTokens.POSITION)

        # keep 'missing remotes' at the end
        if not self.remotes:
            if mtod == ManifestsTypeOfData.DEEP or mtod == ManifestsTypeOfData.FUTURE:
                present_dtt.append(DescribeToTokens.MISSING_REMOTES)
        if not present_dtt:
            present_dtt.append(DescribeToTokens.NONE)

        # return res, able
        return self._describe_to_token_output(
            present_dtt, ljust, mtod, sha1, bare_dm_status
        )

    def _describe_to_token_output(  # noqa: C901
        self,
        present_dtt: List[DescribeToTokens],
        ljust: int,
        mtod: ManifestsTypeOfData,
        sha1: str,
        bare_dm_status: Optional[GitBareStatus] = None,
    ) -> Tuple[ui.Token, ui.Token]:
        # 1st figure out colors
        cb = ui.green  # color (for) branch
        cs = ui.red  # color (for) SHA1
        ct = ui.brown  # color (for) tag
        if mtod == ManifestsTypeOfData.DEEP or mtod == ManifestsTypeOfData.FUTURE:
            cb = cs = mtod_get_main_color(mtod)
        res: List[ui.Token] = []
        able: List[ui.Token] = []

        # 2nd detect last element for 'ljust' to apply
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
            elif e == DescribeToTokens.POSITION:
                if (
                    mtod == ManifestsTypeOfData.DEEP
                    or mtod == ManifestsTypeOfData.FUTURE  # noqa: W503
                ):
                    if bare_dm_status:
                        tmp_res, tmp_able, ljust = bare_dm_status.describe_position(
                            ljust, self.sha1
                        )
                        res += tmp_res
                        able += tmp_able
                        # TODO: any correction for 'ljust'?
                    else:
                        if self.sha1:
                            res += [ui.red, f"?? {sha1}".ljust(this_ljust), ui.reset]
                            able += [ui.red, f"?? {self.sha1}", ui.reset]
                            ljust -= 3 + 7 + 1
                        else:
                            res += [ui.red, "?? commit".ljust(this_ljust), ui.reset]
                            able += [ui.red, "?? commit", ui.reset]
                            ljust -= 9 + 1
            elif e == DescribeToTokens.MISSING_REMOTES:
                res += [ui.red, "(missing remote)".ljust(this_ljust), ui.reset]
                able += [ui.red, "(missing remote)", ui.reset]
                ljust -= 16 + 1  # len of "(missing remote) "
            else:  # DescribeToTokens.NONE:
                res += [" ".ljust(this_ljust)]
                able += [" "]
        return res, able

    def len_of_describe(
        self,
        mtod: ManifestsTypeOfData = ManifestsTypeOfData.LOCAL,
        bare_dm_status: Optional[GitBareStatus] = None,
    ) -> int:
        res, _ = self.describe_to_tokens(0, mtod, bare_dm_status)  # 0 cancel alignment
        return len_of_cli_ui(res)
