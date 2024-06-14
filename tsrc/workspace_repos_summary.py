"""
Workspace Repos Summary

harmonize the GIT repository printouts
along all kinds of use-cases, like:
* manifest command
* status command

All classes and functions here should not
change any data, just to display it properly
"""

import copy
from collections import OrderedDict
from enum import Enum, unique
from typing import Dict, List, Tuple, Union

import cli_ui as ui

from tsrc.errors import InvalidConfig, MissingRepo
from tsrc.git_remote import remote_urls_are_same
from tsrc.groups_to_find import GroupsToFind
from tsrc.local_future_manifest import get_local_future_manifests_manifest_and_repos
from tsrc.manifest import Manifest, RepoNotFound, load_manifest
from tsrc.manifest_common import ManifestGetRepos, ManifestGroupNotFound
from tsrc.pcs_repo import PCSRepo
from tsrc.repo import Repo, TypeOfDescribeBranch
from tsrc.status_endpoint import Status
from tsrc.utils import len_of_cli_ui
from tsrc.workspace import Workspace

StatusOrError = Union[Status, Exception]


@unique
class TypeOfDataInRegardOfTime(Enum):
    PRESENT = 1
    DEEP = 2
    FUTURE = 3


class WorkspaceReposSummary:
    def __init__(
        self,
        workspace: Workspace,
        gtf: GroupsToFind,
        only_manifest: bool = False,
        manifest_marker: bool = True,
        future_manifest: bool = True,
        use_same_future_manifest: bool = False,
    ) -> None:
        self.workspace = workspace
        self.gtf = gtf
        self.is_manifest_marker = manifest_marker
        self.is_future_manifest = future_manifest
        self.use_same_future_manifest = use_same_future_manifest

        # defaults
        self.statuses: Dict[str, StatusOrError] = {}
        self.dm: Union[PCSRepo, None] = None
        self.only_manifest = only_manifest
        self.apprise: bool = False

        # local Future Manifest
        self.lfm: Union[Manifest, None] = None
        self.lfm_repos: Union[Dict[str, Repo], None] = None

        # helpers
        self.clone_all_repos = workspace.config.clone_all_repos

        # alignment
        self.max_dest = 0  # DEST
        self.max_dm_desc = 0  # DM description
        self.max_fm_desc = 0  # FM description
        self.max_desc = 0  # Description
        self.max_a_block = 0  # aprise block

        # needed for evaluating of missing Group(s)
        self.must_find_all_groups = False

        # for detection of <something> is empty
        self.d_m_repo_found_some = False
        self.f_m_leftovers_displayed = (
            False  # so FM leftovers will be displayed just once
        )

    """General use, publicaly callable"""

    def dry_check_future_manifest(self) -> None:
        """Used when we do not have Repos
        and statuses from Workspace"""
        # when there is no 'statuses' from Workspace
        f_m_repos = self._ready_f_m_repos(on_manifest_only=True)
        self.max_fm_desc = self._check_max_fm_desc(f_m_repos)
        if self.max_fm_desc > 0:
            self.apprise = True

        # calculate max_dest
        self.max_dest = self._check_max_dest(None, f_m_repos)

        if self.max_dest > 0:
            self._describe_future_manifest_leftovers(
                self.workspace, f_m_repos, alone_print=True
            )
        else:
            self._describe_workspace_is_empty()

    def ready_data(
        self,
        statuses: Dict[str, StatusOrError],
        dm: Union[PCSRepo, None],
        apprise: bool = False,
    ) -> None:
        """Used to fill the data from statuses
        of Workspace Repos"""
        # provide everything besides 'Workspace'
        self.statuses = statuses
        self.dm = dm  # 'dm' is also a mark if to display Deep Manifest block
        self.apprise = apprise
        # local variables
        self.d_m_root_point = False

        self.clone_all_repos = False
        if self.workspace.config.clone_all_repos is True:
            self.clone_all_repos = True

    def summary(self) -> None:
        """
        Called to print all the reasonable data
        of Workspace, when there are some
        """
        # get max (current) description
        self.max_desc = self._check_max_desc(self.workspace, self.statuses)

        # future manifest repos
        f_m_repos: Union[List[Repo], None] = None  # for future manifest leftovers
        f_m_repos = self._ready_f_m_repos()
        self.max_fm_desc = self._check_max_fm_desc(f_m_repos)

        # let us see if we can find Deep Manifest
        deep_manifest = self._get_deep_manifest(
            self.workspace,
            self.dm,
            self.statuses,
        )

        # prepare 'd_m_repos' to be used for leftovers
        d_m_repos: Union[List[Repo], None] = None
        if deep_manifest:
            mgr = ManifestGetRepos(
                self.workspace, deep_manifest, clone_all_repos=self.clone_all_repos
            )
            d_m_repos, self.must_find_all_groups, self.gtf = mgr.by_groups(
                self.gtf, self.must_find_all_groups
            )

        # calculate max len of Deep Manifest's Description
        self.max_dm_desc = self._check_max_dm_desc(
            # self.workspace,
            self.dm,
            d_m_repos,
        )

        # alignment for 'dest'
        self.max_dest = self._check_max_dest(deep_manifest, f_m_repos)

        # calculate max apprise block
        if self.apprise is True:
            self.max_a_block = self._check_max_a_block()

        # deepcopy before calling 'pop'(s)
        deep_manifest_orig = copy.deepcopy(deep_manifest)

        # this should always ensure that items will be sorted by key
        #        has_d_m_d: OrderedDict[str, bool] = self._sort_based_on_d_m(
        #            has_d_m_d, d_m_repos, deep_manifest
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
            mgr = ManifestGetRepos(
                self.workspace, deep_manifest, clone_all_repos=self.clone_all_repos
            )
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
            self._describe_deep_manifest_leftovers(
                self.workspace,
                deep_manifest,
                d_m_repos,
                f_m_repos,
            )

        # recollect Future Manifest leftovers
        if f_m_repos:
            self._describe_future_manifest_leftovers(self.workspace, f_m_repos)

    """Groups related: check"""

    def must_match_all_groups(self) -> None:
        is_all_found, missing_groups = self.gtf.all_found()
        if is_all_found is False:
            for missing_group in missing_groups:
                raise ManifestGroupNotFound(missing_group)

    """common helpers"""

    def _m_prepare_for_leftovers_regardles_branch(
        self,
        m_repo: Union[Repo, None],
        m_repos: Union[List[Repo], None],
    ) -> Union[Repo, None]:
        """Leftovers processing:
        if found in list, eliminate it.
        when done on all, what is left is worth displaying

        leftover = a (Repo) record in current Manifest
        that is not present in the workspace"""

        r_repo: Union[Repo, None] = None
        if m_repo:
            if m_repos:
                is_found, this_index = self._compare_repo_regardles_branch(
                    m_repo, m_repos
                )
                if is_found is True and this_index >= 0:
                    r_repo = copy.deepcopy(m_repo)
                    m_repos.pop(this_index)
        return r_repo

    def _repo_matched_manifest_dest(
        self,
        workspace: Workspace,
        ref_manifest: Union[Manifest, None],
        dest: str,
    ) -> Tuple[bool, Union[Repo, None]]:
        """checks if repo on given 'dest'
        matches the repo in referenced Manifest"""
        m_repo = None
        if not ref_manifest:
            return False, None
        try:
            m_repo = ref_manifest.get_repo(dest)
        except RepoNotFound:
            return False, None

        # we have to make sure provided 'groups' does match referenced Manifest
        mgr = ManifestGetRepos(
            workspace, ref_manifest, clone_all_repos=self.clone_all_repos
        )
        m_repos, self.must_find_all_groups, self.gtf = mgr.by_groups(
            self.gtf, self.must_find_all_groups
        )
        if not m_repos:
            return False, None

        if m_repo:
            # use configured local_manifest as reference
            workspace_manifest = workspace.local_manifest.get_manifest()
            return self._repo_found_regardles_branch(
                workspace_manifest, m_repo, m_repos, dest
            )
        return False, None

    def _repo_found_regardles_branch(
        self,
        this_manifest: Manifest,
        m_repo: Repo,
        m_repos: List[Repo],
        dest: str,
    ) -> Tuple[bool, Union[Repo, None]]:
        """to proclaiming "same repo" we have to have:
        * found repo in this Manifest (filtered by groups)
        * (!) ignore comparsion of this Manifest repo branch
        * same destination,
        * same remote found as in local_manifest"""
        mgr = ManifestGetRepos(
            self.workspace, this_manifest, clone_all_repos=self.clone_all_repos
        )
        repos, self.must_find_all_groups, self.gtf = mgr.by_groups(
            self.gtf, self.must_find_all_groups
        )
        for repo in repos:
            is_found, _ = self._compare_repo_regardles_branch(repo, m_repos)
            if is_found is True:
                if repo.dest == dest:
                    for r_remote in repo.remotes:
                        for m_repo in m_repos:
                            for s_remote in m_repo.remotes:
                                if (
                                    remote_urls_are_same(r_remote.url, s_remote.url)
                                    is True
                                ):
                                    return True, m_repo
        return False, None

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
                        if remote_urls_are_same(this_remote.url, remote.url) is True:
                            return True, index
        return False, -1

    def _compare_ui_token(self, a: List[ui.Token], b: List[ui.Token]) -> bool:
        if len(a) != len(b):
            return False
        for id, i in enumerate(a):
            if i != b[id]:
                return False
        return True

    """Deep Manifest (only): checks"""

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

    """Deep Manifest (only): Sort-related"""

    def _get_deep_manifest(
        self,
        workspace: Workspace,
        sm: Union[PCSRepo, None],
        statuses: Dict[str, StatusOrError],
    ) -> Union[Manifest, None]:
        """
        obtain Deep Manifest if there is one
        """
        d_m = None
        if sm:
            try:
                # we have to load Deep Manifest, so why not also return it
                d_m = load_manifest(workspace.root_path / sm.dest / "manifest.yml")
            except InvalidConfig as error:
                ui.error("Failed to load Deep Manifest:", error)
                return None

            # side-quest: check Deep Manifest for root point
            self.d_m_root_point = self._check_d_m_root_point(
                workspace, statuses, d_m, sm.dest
            )

        return d_m

    def _sort_based_on_d_m(
        self,
        # has_d_m_d: collections.OrderedDict[str, bool],
        has_d_m_d: Dict[str, bool],
        d_m_repos: Union[List[Repo], None],
        deep_manifest: Union[Manifest, None],
    ) -> "OrderedDict[str, bool]":
        # sort based on: bool: is there a Deep Manifest corelated repository?
        s_has_d_m_d: OrderedDict[str, bool] = OrderedDict()
        if not self.dm:  # do not sort if there is no reason
            s_has_d_m_d = OrderedDict(has_d_m_d)
            return s_has_d_m_d
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
                d_m_repo_found: bool = False
                if self.dm:
                    d_m_repo_found, _ = self._repo_matched_manifest_dest(
                        self.workspace,
                        deep_manifest,
                        dest,
                    )
                has_d_m_d[dest] = d_m_repo_found
                if d_m_repo_found is True:
                    self.d_m_repo_found_some = True
        return has_d_m_d

    """Future Manifest (only): gathering"""

    def _ready_f_m_repos(
        self, on_manifest_only: bool = False
    ) -> Union[List[Repo], None]:
        f_m_repos: Union[List[Repo], None] = None
        if (
            self.workspace.config.manifest_branch
            != self.workspace.config.manifest_branch_0  # noqa: W503
            and self.is_future_manifest is True  # noqa: W503
        ):
            report_skip_fm_update: bool = False
            (
                self.lfm,
                self.lfm_repos,
                self.must_find_all_groups,
                self.gtf,
                report_skip_fm_update,
            ) = get_local_future_manifests_manifest_and_repos(
                self.workspace,
                self.gtf,
                on_manifest_only=True,
                must_find_all_groups=self.must_find_all_groups,
                use_same_future_manifest=self.use_same_future_manifest,
            )
            if report_skip_fm_update is True:
                ui.info_2("Skiping update of: Future Manifest")

            if self.lfm_repos:
                f_m_repos = []
                for dest, repo in self.lfm_repos.items():
                    if dest and repo:
                        # filter the case, when we want only to consider Manifest repo
                        if self.only_manifest is True:
                            for remote in repo.remotes:
                                if (
                                    remote_urls_are_same(
                                        self.workspace.config.manifest_url, remote.url
                                    )
                                    is True
                                ):
                                    f_m_repos.append(repo)
                                    break
                        else:
                            f_m_repos.append(repo)
        return f_m_repos

    """alignment calculations part"""

    def _check_max_dest(
        self, deep_manifest: Union[Manifest, None], f_m_repos: Union[List[Repo], None]
    ) -> int:
        """consider for max length calculation:
        * 'statuses' to get destination names
            + if not present, just ignore
        * Deep Manifest destination names,
        * Future Manifest destination names
        """
        max_dest = 0
        max_dest_dm = 0
        max_dest_fm = 0
        if self.statuses:
            # this is correct regardles of 'self.only_manifest'
            max_dest = max(len(x) for x in self.statuses.keys())

        if deep_manifest:
            mgr = ManifestGetRepos(
                self.workspace, deep_manifest, clone_all_repos=self.clone_all_repos
            )
            d_m_repos, self.must_find_all_groups, self.gtf = mgr.by_groups(
                self.gtf, self.must_find_all_groups
            )
            if d_m_repos:
                if self.only_manifest is True:
                    for d_m_repo in d_m_repos:
                        for remote in d_m_repo.remotes:
                            if (
                                remote_urls_are_same(
                                    self.workspace.config.manifest_url, remote.url
                                )
                                is True
                            ):
                                max_dest_dm = len(d_m_repo.dest)
                                # TODO: break both of the loops
                                break
                else:
                    max_dest_dm = max(len(x.dest) for x in d_m_repos)

        max_dest_fm = self._check_max_dest_fm_part(f_m_repos)

        return max(max_dest_dm, max_dest, max_dest_fm)

    def _check_max_dest_fm_part(
        self,
        f_m_repos: Union[List[Repo], None],
    ) -> int:
        max_dest_fm: int = 0
        if f_m_repos:
            if self.only_manifest is True:
                fm_dest_found: bool = False
                for repo in f_m_repos:
                    for remote in repo.remotes:
                        if (
                            remote_urls_are_same(
                                self.workspace.config.manifest_url, remote.url
                            )
                            is True
                        ):
                            max_dest_fm = len(repo.dest)
                            fm_dest_found = True  # do not need go through other repos
                            break
                    if fm_dest_found is True:
                        break
            else:
                max_dest_fm = max(len(x.dest) for x in f_m_repos)
        return max_dest_fm

    def _check_max_dm_desc(
        self,
        dm: Union[PCSRepo, None],
        d_m_repos: Union[List[Repo], None],
    ) -> int:
        max_dm_desc = 0
        if d_m_repos:
            if self.only_manifest is True:
                for repo in d_m_repos:
                    for remote in repo.remotes:
                        if (
                            remote_urls_are_same(
                                self.workspace.config.manifest_url, remote.url
                            )
                            is True
                        ):
                            return repo.len_of_describe_branch()
            else:
                max_dm_desc = max(x.len_of_describe_branch() for x in d_m_repos)
        return max_dm_desc

    def _check_max_fm_desc(
        self,
        f_m_repos: Union[List[Repo], None],
    ) -> int:
        max_f_branch = 0
        if f_m_repos:
            max_f_branch = max(x.len_of_describe_branch() for x in f_m_repos)
        return max_f_branch

    def _check_max_desc(
        self,
        workspace: Workspace,
        statuses: Dict[str, StatusOrError],
    ) -> int:
        this_list: List[int] = []
        for _, status in statuses.items():
            if isinstance(status, Status):
                # TODO: ERROR: this check Local Manifest, not current state
                # this_list.append(status.manifest.repo.len_of_describe_branch())
                this_list.append(status.git.len_of_describe_branch())
        if this_list:
            return max(this_list)
        else:
            return 0

    def _check_max_a_block(
        self,
    ) -> int:
        max_a_block: int = 4
        if self.lfm and self.max_fm_desc > 0:
            max_a_block += self.max_fm_desc + 3  # 3 == len("<< ")
        if self.max_desc > 0:
            max_a_block += self.max_desc + 1  # 1 == space after 'desc'
        else:
            max_a_block += 4  # 4 == len("::: ")
        return max_a_block

    """describe part: core"""

    def _core_message_print(
        self,
        deep_manifest: Union[Manifest, None],
        s_has_d_m_d: OrderedDict,
        d_m_repos: Union[List[Repo], None] = None,
        f_m_repos: Union[List[Repo], None] = None,
    ) -> None:
        """
        Columns in this print may contain:
        * '*'
        * Destination of Repository
        * [ Deep Manifest Description ]=
        * ( Future Manifest Description
        * comparison with
        * Description of Repository )
        * GIT description and status
        * Manifest Marker
        """
        self._core_message_header()

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

            # do not report further if there is Error, just print it
            if isinstance(status, MissingRepo) or isinstance(status, Exception):
                message += self._describe_deep_manifest(
                    False, None, dest, None, self.max_dm_desc
                )
                message += self._describe_status(status, None)
                ui.info(*message)
                continue

            # describe Deep Manifest field (if present and enabled)
            message += self._describe_deep_manifest_column(
                deep_manifest, dest, d_m_repo, d_m_repo_found, d_m_repos
            )

            # describe Future Manifest (if present and enabled)
            # also describe GIT description and status along with it
            fm_col = self._describe_future_manifest_column(dest, status, f_m_repos)
            fm_col_len = len_of_cli_ui(fm_col)
            if fm_col_len > 0:
                fm_col_len += 1
            if not f_m_repos:
                # just cancel apprise block alignment
                fm_col_len = self.max_a_block
            message += fm_col

            # final Manifest-only extra markings
            if self.is_manifest_marker is True and isinstance(status, Status):
                for this_remote in status.manifest.repo.remotes:
                    if (
                        remote_urls_are_same(
                            this_remote.url, self.workspace.config.manifest_url
                        )
                        is True
                    ):
                        message += self._describe_on_manifest(
                            align_before=(self.max_a_block - fm_col_len)
                        )
                        break

            ui.info(*message)

    def _core_message_header(self) -> None:
        if self.max_dest > 0:
            if self.statuses:
                ui.info_2("Before possible GIT statuses, Workspace reports:")
            else:
                ui.info_2("Workspace reports:")
            message: List[ui.Token] = []
            message += ["Destination"]
            if self.max_dm_desc > 0:
                message += ["[Deep Manifest description]"]

            if self.max_fm_desc > 0:
                message += ["(Future Manifest description)"]
            ui.info_2(*message)

    def _describe_workspace_is_empty(self) -> None:
        ui.info_2("Workspace is empty")

    """describe part: columns"""

    def _describe_future_manifest_column(
        self,
        dest: str,
        status: StatusOrError,
        f_m_repos: Union[List[Repo], None] = None,
    ) -> List[ui.Token]:
        message: List[ui.Token] = []
        is_empty_fm_desc = True
        if self.lfm_repos:
            f_m_repo_found, f_m_repo = self._repo_matched_manifest_dest(
                self.workspace,
                self.lfm,
                dest,
            )
            if f_m_repo_found is True and f_m_repo:
                message += self._describe_status(status, f_m_repo)
                is_empty_fm_desc = False
                # eliminate from 'f_m_repos' as well
                self._m_prepare_for_leftovers_regardles_branch(
                    f_m_repo,
                    f_m_repos,
                )
        else:
            message += self._describe_status(status, None)
            is_empty_fm_desc = False
        if is_empty_fm_desc is True:
            message += self._describe_status(status, None, fm_dest_is_empty=True)
        return message

    def _describe_deep_manifest_column(
        self,
        deep_manifest: Union[Manifest, None],
        dest: str,
        d_m_repo: Union[Repo, None],
        d_m_repo_found: bool,
        d_m_repos: Union[List[Repo], None],
    ) -> List[ui.Token]:
        message: List[ui.Token] = []
        r_d_m_repo: Union[Repo, None] = None
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
            self.max_dm_desc,
        )
        return message

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
            desc, _ = d_m_repo.describe_branch(self.max_dm_desc)
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
            if self.max_dm_desc > 0:
                if self.d_m_root_point is True:
                    message += [" ".ljust(self.max_dm_desc + 2 + 2 + 1)]
                else:
                    message += [" ".ljust(self.max_dm_desc + 2 + 2)]
        return message

    def _describe_status(
        self,
        status: StatusOrError,
        apprise_repo: Union[Repo, None],
        fm_dest_is_empty: bool = False,
    ) -> List[ui.Token]:
        """Return a list of tokens suitable for ui.info()."""
        if isinstance(status, MissingRepo):
            return [ui.red, "error: missing repo"]
        if isinstance(status, Exception):
            return [ui.red, "error: ", status]
        git_status: List[ui.Token] = []
        git_status += status.git.describe_pre_branch()

        if not git_status:
            if self.apprise is True and self.max_fm_desc > 0:
                if fm_dest_is_empty is True:
                    apprise_repo = None
                git_status += self._describe_status_apprise_branch(
                    status.git.describe_branch(),
                    apprise_repo,
                )
            else:
                git_status += status.git.describe_branch()
            git_status += status.git.describe_post_branch()

        manifest_status = status.manifest.describe()
        return git_status + manifest_status

    def _describe_status_apprise_branch(
        self,
        ui_branch: List[ui.Token],
        apprise_repo: Union[Repo, None],
    ) -> List[ui.Token]:
        """usefull for Future Manifest"""
        message: List[ui.Token] = []
        message += [ui.cyan, "("]
        if apprise_repo:
            desc, desc_cmp = apprise_repo.describe_branch(
                self.max_fm_desc, TypeOfDescribeBranch.FM
            )
            message += desc
            if self._compare_ui_token(desc_cmp, ui_branch) is True:
                message += [ui.blue, "=="]
            else:
                message += [ui.blue, "<<"]
        else:
            if self.lfm and self.max_fm_desc > 0:
                message += [" ".ljust(self.max_fm_desc), "<<"]
        message += ui_branch
        message += [ui.cyan, ")", ui.reset]
        return message

    def _describe_status_apprise_branch_empty_space(
        self,
    ) -> List[ui.Token]:
        if self.max_a_block > 0:
            return [" ".ljust(self.max_a_block)]
        return []

    """describe part: marker"""

    def _describe_on_manifest(
        self,
        tod: TypeOfDataInRegardOfTime = TypeOfDataInRegardOfTime.PRESENT,
        dest_has_aprise_desc: bool = True,
        align_before: int = 0,
    ) -> List[ui.Token]:
        message: List[ui.Token] = []
        if align_before > 0:
            message += [" ".ljust(align_before)]

        if tod == TypeOfDataInRegardOfTime.PRESENT:
            message += [ui.reset]

        if tod == TypeOfDataInRegardOfTime.DEEP:
            # TODO: move this before calling the function
            if dest_has_aprise_desc is False:
                if self.apprise is True and self.max_fm_desc > 0:
                    message += self._describe_status_apprise_branch_empty_space()
                else:
                    message += [" ".ljust(self.max_desc)]
            message += [ui.purple]

        if tod == TypeOfDataInRegardOfTime.FUTURE:
            message += [ui.cyan]

        message += ["~~ MANIFEST"]
        return message

    """describe part: leftovers"""

    def _describe_deep_manifest_leftovers(
        self,
        workspace: Workspace,
        deep_manifest: Manifest,
        d_m_repos: Union[List[Repo], None],
        f_m_repos: Union[List[Repo], None],
    ) -> None:
        if not d_m_repos:
            return None
        is_manifest_marker: bool = False
        is_manifest_marker_displayed: bool = False
        for leftover in d_m_repos:

            # check for Manifest Marker
            if self.is_manifest_marker is True and is_manifest_marker is False:
                for remote in leftover.remotes:
                    if (
                        remote_urls_are_same(workspace.config.manifest_url, remote.url)
                        is True
                    ):
                        is_manifest_marker = True  # block repeated checking
                        break
            if self.only_manifest is True and is_manifest_marker is False:
                continue

            is_manifest_marker_displayed = self._describe_deep_manifest_leftovers_repo(
                workspace,
                deep_manifest,
                leftover,
                f_m_repos,
                is_manifest_marker,
                is_manifest_marker_displayed,
            )

    def _describe_deep_manifest_leftovers_repo(
        self,
        workspace: Workspace,
        deep_manifest: Manifest,
        leftover: Repo,
        f_m_repos: Union[List[Repo], None],
        is_manifest_marker: bool,
        is_manifest_marker_displayed: bool,
    ) -> bool:
        # return: 'is_manifest_marker_displayed'
        message: List[ui.Token] = []
        if (self.workspace.root_path / leftover.dest).is_dir():
            message += [ui.reset, "*", ui.purple]
        else:
            message += [ui.purple, "*"]
        message += [leftover.dest.ljust(self.max_dest)]

        message += [ui.brown, "[", ui.purple]
        desc, _ = leftover.describe_branch(self.max_dm_desc, TypeOfDescribeBranch.DM)
        message += desc
        if self.d_m_root_point is True:
            message += [ui.brown, "] ", ui.reset]
        else:
            message += [ui.brown, "]", ui.reset]

        dest_has_aprise_desc: bool = False
        if self.lfm_repos and f_m_repos:
            _, this_repo = self._repo_found_regardles_branch(
                deep_manifest, leftover, f_m_repos, leftover.dest
            )
            if this_repo:
                # found Future Manifest leftovers in Deep Manifest Leftovers
                if self.is_future_manifest is True:
                    message += self._describe_status_apprise_branch(
                        # ":::" is one of few not valid branch name,
                        # therefore is suitable to be mark for N/A
                        [ui.reset, ":::"],
                        self.lfm_repos[leftover.dest],
                    )
                    dest_has_aprise_desc = True
                self._m_prepare_for_leftovers_regardles_branch(this_repo, f_m_repos)

        if is_manifest_marker is True and is_manifest_marker_displayed is False:
            # add Manifest mark with proper color
            message += self._describe_on_manifest(
                TypeOfDataInRegardOfTime.DEEP, dest_has_aprise_desc
            )
            is_manifest_marker_displayed = True

        ui.info(*message)
        return is_manifest_marker_displayed

    def _describe_future_manifest_leftovers(
        self,
        workspace: Workspace,
        f_m_repos: Union[List[Repo], None],
        alone_print: bool = False,
    ) -> None:
        if self.f_m_leftovers_displayed is True:
            return
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
                self._describe_future_manifest_leftover_repo(
                    workspace,
                    leftover,
                )
        self.f_m_leftovers_displayed = True

    def _describe_future_manifest_leftover_repo(
        self,
        workspace: Workspace,
        leftover: Repo,
    ) -> None:
        # do not display FM leftovers when FM is disabled
        if self.is_future_manifest is False:
            return

        is_future_manifest = False
        for remote in leftover.remotes:
            if remote_urls_are_same(workspace.config.manifest_url, remote.url) is True:
                is_future_manifest = True
                break
        if self.only_manifest is True and is_future_manifest is False:
            return

        message: List[ui.Token] = []
        if (self.workspace.root_path / leftover.dest).is_dir():
            message += [ui.reset, "*", ui.cyan]
        else:
            message += [ui.cyan, "*"]
        message += [leftover.dest.ljust(self.max_dest)]
        if self.max_dm_desc > 0:
            message += self._describe_future_manifest_leftovers_empty_space(
                self.max_dm_desc
            )
        a_message: List[ui.Token] = []
        if self.apprise is True:
            # ":::" is one of few not valid branch name,
            # therefore is suitable to be mark for N/A
            a_message = self._describe_status_apprise_branch(
                [ui.reset, ":::"], leftover
            )
            message += a_message
        if self.is_manifest_marker is True and is_future_manifest is True:
            # add Manifest mark with proper color
            a_block_len: int = 0
            if a_message:
                a_block_len = len_of_cli_ui(a_message) + 1
            message += self._describe_on_manifest(
                TypeOfDataInRegardOfTime.FUTURE,
                align_before=(self.max_a_block - a_block_len),
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
