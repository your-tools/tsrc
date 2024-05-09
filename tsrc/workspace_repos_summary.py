"""
Workspace Repos Summary

harmonize the GIT repository printouts
along all kinds of use-cases, like:
* manifest command
* status command

All classes and functions here should not
change any data, just to present it properly
"""

import copy
from collections import OrderedDict
from enum import Enum, unique
from pathlib import Path
from typing import Dict, List, Tuple, Union

import cli_ui as ui

from tsrc.errors import InvalidConfig, MissingRepo
from tsrc.git import run_git_captured
from tsrc.groups_to_find import GroupsToFind
from tsrc.local_future_manifest import get_local_future_manifests_manifest_and_repos
from tsrc.manifest import Manifest, RepoNotFound, load_manifest
from tsrc.manifest_common import ManifestGetRepos, ManifestGroupNotFound
from tsrc.pcs_repo import PCSRepo
from tsrc.repo import Repo, TypeOfDescribeBranch
from tsrc.status_endpoint import Status
from tsrc.workspace import Workspace

StatusOrError = Union[Status, Exception]


@unique
class TypeOfDataInRegardOfTime(Enum):
    PRESENT = 1
    FUTURE = 2


class WorkspaceReposSummary:
    def __init__(
        self,
        workspace: Workspace,
        gtf: GroupsToFind,
    ) -> None:
        self.workspace = workspace
        self.gtf = gtf
        # this variable is possibly obsolete
        self.must_find_all_groups = False  # possibly obsolete

        # defaults
        self.statuses: Dict[str, StatusOrError] = {}
        self.dm: Union[PCSRepo, None] = None
        self.only_manifest: bool = False
        self.apprise: bool = False

        self.lfm: Union[Manifest, None] = None
        self.lfm_repos: Union[Dict[str, Repo], None] = None

        # alignment
        self.max_dest = 0
        self.max_m_branch = 0
        self.max_f_branch = 0

        # for detection of <something> is empty
        self.d_m_repo_found_some = False

    def ready_data(
        self,
        statuses: Dict[str, StatusOrError],
        dm: Union[PCSRepo, None],
        only_manifest: bool = False,
        apprise: bool = False,
    ) -> None:
        # provide everything besides 'Workspace'
        self.statuses = statuses
        self.dm = dm
        self.only_manifest = only_manifest
        self.apprise = apprise
        # local variables
        self.d_m_root_point = False

        self.clone_all_repos = False
        if self.workspace.config.clone_all_repos is True:
            self.clone_all_repos = True

    def _ready_f_m_repos(
        self, on_manifest_only: bool = False
    ) -> Union[List[Repo], None]:
        f_m_repos: Union[List[Repo], None] = None
        if (
            self.workspace.config.manifest_branch
            != self.workspace.config.manifest_branch_0  # noqa: W503
        ):
            (
                self.lfm,
                self.lfm_repos,
                self.must_find_all_groups,
                self.gtf,
            ) = get_local_future_manifests_manifest_and_repos(
                self.workspace,
                self.gtf,
                on_manifest_only=True,
                must_find_all_groups=self.must_find_all_groups,
            )
            if self.lfm_repos:
                f_m_repos = []
                for dest, repo in self.lfm_repos.items():
                    if dest and repo:
                        f_m_repos.append(repo)
        return f_m_repos

    def _alignment_correction_when_on_only_manifest(
        self,
        manifest: Union[Manifest, None],
        f_m_repos: Union[List[Repo], None],
    ) -> None:
        if self.only_manifest is False:
            self.max_dest = self._correct_max_dest(manifest, f_m_repos)
        else:
            self.max_m_branch = 0
            self.max_f_branch = 0

    def dry_check_future_manifest(self, only_manifest: bool = False) -> None:
        # when there is no 'statuses' from Workspace
        self.only_manifest = only_manifest
        f_m_repos = self._ready_f_m_repos(on_manifest_only=True)
        self.max_f_branch = self._max_len_f_m_branch(f_m_repos)

        # zero-out alignment that does not come into consideration
        # * in here, there cannot be Deep Manifest as there are no normal Workspace Repos
        self._alignment_correction_when_on_only_manifest(None, f_m_repos)

        self._describe_future_manifest_leftovers(
            self.workspace, f_m_repos, alone_print=True
        )

    def _sort_based_on_d_m(
        self,
        # has_d_m_d: collections.OrderedDict[str, bool],
        has_d_m_d: Dict[str, bool],
        d_m_repos: Union[List[Repo], None],
        deep_manifest: Union[Manifest, None],
    ) -> "OrderedDict[str, bool]":
        # sort based on: bool: is there a Deep Manifest corelated repository?
        s_has_d_m_d: OrderedDict[str, bool] = OrderedDict()
        for key in sorted(has_d_m_d, key=has_d_m_d.__getitem__):
            s_has_d_m_d[key] = has_d_m_d[key]
            # following part only prepare leftovers
            # to calculate 'self.repo_found_some'
            if self.d_m_repo_found_some is False:
                d_m_repo_found, d_m_repo = self._repo_matched_manifest_dest(
                    self.workspace,
                    deep_manifest,
                    key,
                )
                # eliminate Deep Manifest record if found in workspace repos
                if d_m_repo_found is True:
                    self._m_prepare_for_leftovers_regardles_branch(
                        d_m_repo,
                        d_m_repos,
                    )

        if d_m_repos:
            self.d_m_repo_found_some = True
        del d_m_repos

        return s_has_d_m_d

    def _prepare_for_sort_on_d_m(
        self,
        deep_manifest: Union[Manifest, None],
    ) -> Dict[str, bool]:
        # ) -> OrderedDict[str, bool]:
        # # if we want to sort the 'dest' as well
        # o_stats = OrderedDict(sorted(self.statuses.items()))
        # has_d_m_d: OrderedDict[str, bool] = OrderedDict()
        has_d_m_d: Dict[str, bool] = {}
        # for dest in o_stats.keys():
        for dest in self.statuses.keys():
            # following condition is only here to minimize execution
            if self.only_manifest is False or (self.dm and dest == self.dm.dest):
                # produce just [True|False] to be used as key in sorting items
                d_m_repo_found, _ = self._repo_matched_manifest_dest(
                    self.workspace,
                    deep_manifest,
                    dest,
                )
                has_d_m_d[dest] = d_m_repo_found
                if d_m_repo_found is True:
                    self.d_m_repo_found_some = True
        return has_d_m_d

    def must_match_all_groups(self) -> None:
        is_all_found, missing_groups = self.gtf.all_found()
        if is_all_found is False:
            for missing_group in missing_groups:
                raise ManifestGroupNotFound(missing_group)

    def summary(self) -> None:
        # future manifest repos
        f_m_repos: Union[List[Repo], None] = None  # for future manifest leftovers
        f_m_repos = self._ready_f_m_repos()
        self.max_f_branch = self._max_len_f_m_branch(f_m_repos)

        # calculate all Deep_Manifest max branch name length
        # and if Deep_Manifest is found, return it as well
        self.max_m_branch, deep_manifest = self._max_len_manifest_branch(
            self.workspace,
            self.dm,
            self.statuses,
        )

        # prepare 'd_m_repos' to be used for leftovers
        d_m_repos: Union[List[Repo], None] = None
        if deep_manifest:
            mgr = ManifestGetRepos(self.workspace, deep_manifest)
            d_m_repos, self.must_find_all_groups, self.gtf = mgr.by_groups(
                self.gtf, self.must_find_all_groups
            )

        # zero-out alignment that does not come into consideration
        self._alignment_correction_when_on_only_manifest(deep_manifest, f_m_repos)

        # deepcopy before calling 'pop'(s)
        deep_manifest_orig = copy.deepcopy(deep_manifest)

        # this should always ensure that items will be sorted by key
        #        has_d_m_d: OrderedDict[str, bool] = self._prepare_for_sort_on_d_m(
        #            deep_manifest
        #        )
        has_d_m_d: Dict[str, bool] = self._prepare_for_sort_on_d_m(deep_manifest)
        s_has_d_m_d: OrderedDict[str, bool] = self._sort_based_on_d_m(
            has_d_m_d, d_m_repos, deep_manifest
        )

        # bring original deep_manifest back
        deep_manifest = deep_manifest_orig

        # once again prepare for leftovers
        d_m_repos = None
        if deep_manifest:
            mgr = ManifestGetRepos(self.workspace, deep_manifest)
            d_m_repos, self.must_find_all_groups, self.gtf = mgr.by_groups(
                self.gtf, self.must_find_all_groups
            )

        # print main part with current workspace repositories
        self._core_message_print(
            deep_manifest,
            s_has_d_m_d,
            d_m_repos,
            f_m_repos,
        )

        # recollect leftovers only if there is full list
        if deep_manifest:
            if self.only_manifest is False:
                self._describe_deep_manifest_leftovers(
                    deep_manifest,
                    d_m_repos,
                    f_m_repos,
                )

        # recollect Future Manifest leftovers
        if f_m_repos:
            self._describe_future_manifest_leftovers(self.workspace, f_m_repos)

    def _core_message_print(
        self,
        deep_manifest: Union[Manifest, None],
        s_has_d_m_d: OrderedDict,
        d_m_repos: Union[List[Repo], None] = None,
        f_m_repos: Union[List[Repo], None] = None,
    ) -> None:
        """Prints a summary of Workspace repository status.

        Output will be like this:
        * '*': starts the record
        * '/repository_path/': Workspace record
        * '[ .. ]'|'[ .. ]=': Deep Manifest describe (optional)
        (represents some kind of inside block like as if Manifest expands)
        * '(': (optional)
        * '/local Future Manifest description/'
        * '<<'|'=='|'': comparsion of descriptions
        * '/current description/'
        * ')': (optional)
        * '/GIT status/': (optional) anything GIT has to report
        * '~~ MANIFEST ' (optional) (marker for Manifest repo only)
        """
        for dest in s_has_d_m_d.keys():

            status = self.statuses[dest]
            d_m_repo_found = False
            d_m_repo = None
            # following condition is only here to minimize execution
            if self.only_manifest is False or (self.dm and dest == self.dm.dest):
                d_m_repo_found, d_m_repo = self._repo_matched_manifest_dest(
                    self.workspace,
                    deep_manifest,
                    dest,
                )

            if self.dm and dest != self.dm.dest and self.only_manifest is True:
                continue

            message = [ui.green, "*", ui.reset, dest.ljust(self.max_dest)]

            if deep_manifest and self.d_m_repo_found_some is True:
                # get Deep Manifest repo
                # also eliminate from 'd_m_repos'
                r_d_m_repo = self._m_prepare_for_leftovers_regardles_branch(
                    d_m_repo,
                    d_m_repos,
                )
                message += self._describe_deep_manifest(
                    d_m_repo_found,
                    r_d_m_repo,
                    dest,
                    self.dm,
                    self.max_m_branch,
                )

            is_default_describe = True
            if self.lfm_repos:
                f_m_repo_found, f_m_repo = self._repo_matched_manifest_dest(
                    self.workspace,
                    self.lfm,
                    dest,
                )
                if f_m_repo_found is True and f_m_repo:
                    message += self._describe_status(status, f_m_repo)
                    is_default_describe = False
                    # eliminate from 'f_m_repos' as well
                    self._m_prepare_for_leftovers_regardles_branch(
                        f_m_repo,
                        f_m_repos,
                    )
            if is_default_describe is True:
                message += self._describe_status(status, None)

            # final Manifest-only extra markings
            if self.dm and dest == self.dm.dest:
                message += self._describe_on_manifest()

            ui.info(*message)

    """common helpers"""

    def _compare_repo_regardles_branch(
        self,
        repo: Repo,
        in_repo: List[Repo],
    ) -> Tuple[bool, int]:
        """Suitable for using in deletion
        That can be used for preparing leftovers"""
        for index, i in enumerate(in_repo):
            if i.dest == repo.dest:
                for this_remote in repo.remotes:
                    for remote in i.remotes:
                        if this_remote.url == remote.url:
                            return True, index
        return False, -1

    """Deep Manifest related checks"""

    def _repo_matched_manifest_dest(
        self,
        workspace: Workspace,
        ref_manifest: Union[Manifest, None],
        dest: str,
    ) -> Tuple[bool, Union[Repo, None]]:
        """checks if repo on given 'dest'
        matches the repo in Deep Manifest"""
        d_m_repo = None
        if not ref_manifest:
            return False, None
        try:
            d_m_repo = ref_manifest.get_repo(dest)
        except RepoNotFound:
            return False, None

        # we have to make sure provided 'groups' does match Deep Manifest
        mgr = ManifestGetRepos(workspace, ref_manifest)
        d_m_repos, self.must_find_all_groups, self.gtf = mgr.by_groups(
            self.gtf, self.must_find_all_groups
        )
        if not d_m_repos:
            return False, None

        # to proclaiming 'same repo' we have to have:
        # * found in Deep Manifest filtered by groups
        # * (!) ignore Deep Manifest repo branch
        # * same destination,
        # * same remote found as in local_manifest
        # * (!) branch does not have to be the same
        if d_m_repo:
            # use configured local_manifest as reference
            workspace_manifest = workspace.local_manifest.get_manifest()
            return self._repo_found_regardles_branch(
                workspace_manifest, d_m_repo, d_m_repos, dest
            )
        return False, None

    def _repo_found_regardles_branch(
        self,
        this_manifest: Manifest,
        d_m_repo: Repo,
        d_m_repos: List[Repo],
        dest: str,
    ) -> Tuple[bool, Union[Repo, None]]:
        mgr = ManifestGetRepos(self.workspace, this_manifest)
        repos, self.must_find_all_groups, self.gtf = mgr.by_groups(
            self.gtf, self.must_find_all_groups
        )
        for repo in repos:
            is_found, _ = self._compare_repo_regardles_branch(repo, d_m_repos)
            if is_found is True:
                if repo.dest == dest:
                    for r_remote in repo.remotes:
                        for d_m_repo in d_m_repos:
                            for s_remote in d_m_repo.remotes:
                                if r_remote.url == s_remote.url:
                                    return True, d_m_repo
        return False, None

    """Leftovers processing:
    if found in list, eliminate it.
    when done on all, what is left is worth displaying"""

    def _m_prepare_for_leftovers_regardles_branch(
        self,
        d_m_repo: Union[Repo, None],
        d_m_repos: Union[List[Repo], None],
    ) -> Union[Repo, None]:
        """leftover = a (Repo) record in current Deep Manifest
        that is not present in the workspace"""
        r_repo: Union[Repo, None] = None
        if d_m_repo:
            if d_m_repos:
                is_found, this_index = self._compare_repo_regardles_branch(
                    d_m_repo, d_m_repos
                )
                if is_found is True and this_index >= 0:
                    r_repo = copy.deepcopy(d_m_repo)
                    d_m_repos.pop(this_index)
        return r_repo

    def _check_d_m_root_point(
        self,
        workspace: Workspace,
        statuses: Dict[str, StatusOrError],
        d_m: Manifest,
        sm_dest: str,
    ) -> bool:
        """check just Manifest branch from Deep Manifest,
        in order to decide if '=' will be present in the output"""
        for dest, _status in statuses.items():
            if dest == sm_dest:
                try:
                    d_m.get_repo(dest)
                except RepoNotFound:
                    break
                d_m_root_point, _ = self._repo_matched_manifest_dest(
                    workspace, d_m, dest
                )
                return d_m_root_point
        return False

    """alignment calculations part"""

    def _correct_max_dest(
        self, deep_manifest: Union[Manifest, None], f_m_repos: Union[List[Repo], None]
    ) -> int:
        """includes:
        * 'statuses' to get destination names
            + if not present, just ignore
        * Deep Manifest destination names,
        * Future Manifest destination names
        into the max length calculation"""
        max_dest = 0
        max_dest_dm = 0
        max_dest_fm = 0
        if self.statuses:
            max_dest = max(len(x) for x in self.statuses.keys())
        if deep_manifest:
            mgr = ManifestGetRepos(self.workspace, deep_manifest)
            d_m_repos, self.must_find_all_groups, self.gtf = mgr.by_groups(
                self.gtf, self.must_find_all_groups
            )
            if d_m_repos:
                max_dest_dm = max(len(x.dest) for x in d_m_repos)
        if f_m_repos:
            # TODO: Future Manifest also needs to be checked by 'groups'
            max_dest_fm = max(len(x.dest) for x in f_m_repos)
        return max(max_dest_dm, max_dest, max_dest_fm)

    def _max_len_manifest_branch(
        self,
        workspace: Workspace,
        sm: Union[PCSRepo, None],
        statuses: Dict[str, StatusOrError],
    ) -> Tuple[int, Union[Manifest, None]]:
        """calculate maximum lenght for deep manifest branch (if present)
        if found, return also deep manifest repo.
        detect if Deep Manifest will have a root_point (global variable)"""
        max_m_branch = 0
        d_m = None
        if sm:
            try:
                # we have to load Deep Manifest, so why not also return it
                d_m = load_manifest(workspace.root_path / sm.dest / "manifest.yml")
            except InvalidConfig as error:
                ui.error("Failed to load Deep Manifest:", error)
                return 0, None

            # side-quest: check Deep Manifest for root point
            self.d_m_root_point = self._check_d_m_root_point(
                workspace, statuses, d_m, sm.dest
            )
            mgr = ManifestGetRepos(workspace, d_m)
            d_m_repos, self.must_find_all_groups, self.gtf = mgr.by_groups(
                self.gtf, self.must_find_all_groups
            )
            if d_m_repos:
                max_m_branch = max(x.len_of_describe_branch() for x in d_m_repos)

        return max_m_branch, d_m

    def _max_len_f_m_branch(
        self,
        f_m_repos: Union[List[Repo], None],
    ) -> int:
        max_f_branch = 0
        if f_m_repos:
            max_f_branch = max(x.len_of_describe_branch() for x in f_m_repos)
        return max_f_branch

    """describe part"""

    def _describe_deep_manifest(
        self,
        d_m_r_found: bool,
        d_m_repo: Union[Repo, None],
        dest: str,
        sm: Union[PCSRepo, None],
        max_m_branch: int,
    ) -> List[ui.Token]:
        message: List[ui.Token] = []
        if d_m_r_found is True and isinstance(d_m_repo, Repo):
            message += [ui.brown, "[", ui.green]
            desc, _ = d_m_repo.describe_branch(self.max_m_branch)
            message += desc
            if sm and dest == sm.dest:
                if self.d_m_root_point is True:
                    message += [ui.brown, "]=", ui.reset]
                else:
                    message += [ui.brown, "]", ui.reset]
            else:
                if self.d_m_root_point is True:
                    message += [ui.brown, "] ", ui.reset]
                else:
                    message += [ui.brown, "]", ui.reset]
        else:
            if self.only_manifest is False:
                if self.d_m_root_point is True:
                    message += [" ".ljust(self.max_m_branch + 2 + 2 + 1)]
                else:
                    message += [" ".ljust(self.max_m_branch + 2 + 2)]
        return message

    def _describe_status(
        self, status: StatusOrError, apprise_repo: Union[Repo, None]
    ) -> List[ui.Token]:
        """Return a list of tokens suitable for ui.info()."""
        if isinstance(status, MissingRepo):
            return [ui.red, "error: missing repo"]
        if isinstance(status, Exception):
            return [ui.red, "error: ", status]
        git_status: List[ui.Token] = []
        git_status += status.git.describe_pre_branch()

        if not git_status:
            if self.apprise is True:
                git_status += self._describe_status_apprise_branch(
                    status.git.describe_branch(), apprise_repo
                )
            else:
                git_status += status.git.describe_branch()
            git_status += status.git.describe_post_branch()

        manifest_status = status.manifest.describe()
        return git_status + manifest_status

    def _describe_status_apprise_branch(
        self, ui_branch: List[ui.Token], apprise_repo: Union[Repo, None]
    ) -> List[ui.Token]:
        """usefull for Future Manifest"""
        git_status: List[ui.Token] = []
        git_status += [ui.cyan, "("]
        if apprise_repo:
            desc, desc_cmp = apprise_repo.describe_branch(
                self.max_f_branch, TypeOfDescribeBranch.FM
            )
            git_status += desc
            if self._compare_ui_token(desc_cmp, ui_branch) is True:
                git_status += [ui.blue, "=="]
            else:
                git_status += [ui.blue, "<<"]
        else:
            if self.lfm and self.only_manifest is False and self.max_f_branch > 0:
                git_status += [" ".ljust(self.max_f_branch + 3)]  # 3 == len("<< ")
        git_status += ui_branch
        git_status += [ui.cyan, ")", ui.reset]
        return git_status

    def _compare_ui_token(self, a: List[ui.Token], b: List[ui.Token]) -> bool:
        if len(a) != len(b):
            return False
        for id, i in enumerate(a):
            if i != b[id]:
                return False
        return True

    def _describe_deep_manifest_leftovers(
        self,
        deep_manifest: Manifest,
        d_m_repos: Union[List[Repo], None],
        f_m_repos: Union[List[Repo], None],
    ) -> None:
        if not d_m_repos:
            return None
        for leftover in d_m_repos:
            message = [ui.reset, "*", ui.purple, leftover.dest.ljust(self.max_dest)]
            message += [ui.brown, "[", ui.purple]
            desc, _ = leftover.describe_branch(
                self.max_m_branch, TypeOfDescribeBranch.DM
            )
            message += desc
            if self.d_m_root_point is True:
                message += [ui.brown, "] ", ui.reset]
            else:
                message += [ui.brown, "]", ui.reset]
            if self.lfm_repos and f_m_repos:
                _, this_repo = self._repo_found_regardles_branch(
                    deep_manifest, leftover, f_m_repos, leftover.dest
                )
                if this_repo:
                    # found Future Manifest leftovers in Deep Manifest Leftovers
                    message += self._describe_status_apprise_branch(
                        # ":::" is one of few not valid branch name,
                        # therefore is suitable to be mark for N/A
                        [ui.reset, ":::"],
                        self.lfm_repos[leftover.dest],
                    )
                    self._m_prepare_for_leftovers_regardles_branch(this_repo, f_m_repos)

            ui.info(*message)

    def _describe_future_manifest_leftovers(
        self,
        workspace: Workspace,
        f_m_repos: Union[List[Repo], None],
        alone_print: bool = False,
    ) -> None:
        if alone_print is True:
            if f_m_repos:
                if len(f_m_repos) == 1:
                    ui.info_2("Future Manifest's Repo found:")
                else:
                    ui.info_2("Future Manifest's Repos found:")
            else:
                ui.info_2("Empty on Future Manifest's Repo(s)")
        if f_m_repos:
            for leftover in f_m_repos:
                is_future_manifest = False
                for remote in leftover.remotes:
                    if workspace.config.manifest_url == remote.url:
                        is_future_manifest = True
                        break
                # if self.only_manifest is True and do_skip is True:
                if self.only_manifest is True and is_future_manifest is False:
                    continue

                message = [ui.reset, "*", ui.cyan, leftover.dest.ljust(self.max_dest)]
                message += self._describe_future_manifest_leftovers_empty_space(
                    self.max_m_branch
                )
                # ":::" is one of few not valid branch name,
                # therefore is suitable to be mark for N/A
                message += self._describe_status_apprise_branch(
                    [ui.reset, ":::"], leftover
                )
                if is_future_manifest is True:
                    # add Manifest mark with proper color
                    message += self._describe_on_manifest(
                        TypeOfDataInRegardOfTime.FUTURE
                    )
                ui.info(*message)

    def _describe_future_manifest_leftovers_empty_space(
        self,
        max_m_branch: int,
    ) -> List[ui.Token]:
        message: List[ui.Token] = []
        if self.d_m_repo_found_some is True:
            if self.d_m_root_point is True:
                message += [" ".ljust(max_m_branch + 2 + 2 + 1)]
            else:
                message += [" ".ljust(max_m_branch + 2 + 2)]
        return message

    def _describe_on_manifest(
        self, tod: TypeOfDataInRegardOfTime = TypeOfDataInRegardOfTime.PRESENT
    ) -> List[ui.Token]:
        message: List[ui.Token] = []
        if tod == TypeOfDataInRegardOfTime.PRESENT:
            message += [ui.purple]
        if tod == TypeOfDataInRegardOfTime.FUTURE:
            message += [ui.cyan]
        # :: hunt for the best MANIFEST marker is ongoing ::
        message += ["~~ MANIFEST"]
        return message


def get_l_and_r_sha1_of_branch(
    w_r_path: Path,
    dest: str,
    branch: str,
) -> Tuple[Union[str, None], Union[str, None]]:
    """obtain local and remote SHA1 of given branch.
    This is useful when we need to check if we are exactly
    updated with remote down to the commit"""
    rc, l_b_sha = run_git_captured(
        w_r_path / dest,
        "rev-parse",
        "--verify",
        "HEAD",
        check=False,
    )
    if rc != 0:
        return None, None

    _, l_ref = run_git_captured(w_r_path / dest, "symbolic-ref", "-q", "HEAD")
    _, r_ref = run_git_captured(
        w_r_path / dest, "for-each-ref", "--format='%(upstream)'", l_ref
    )
    r_b_sha = None
    if rc == 0:
        tmp_r_ref = r_ref.split("/")
        this_remote = tmp_r_ref[2]
        _, r_b_sha = run_git_captured(
            w_r_path / dest,
            "ls-remote",
            "--exit-code",
            "--head",
            this_remote,
            l_ref,
            check=True,
        )
    if r_b_sha:
        return l_b_sha, r_b_sha.split()[0]
    else:
        return l_b_sha, None
