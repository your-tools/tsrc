"""
Workspace Repos Summary

harmonize the GIT repository printouts
along all kinds of use-cases, like:
* manifest command
* status command

All classes and functions here should not
change any data, just to display it properly
"""

from collections import OrderedDict
from copy import deepcopy
from typing import Dict, List, Tuple, Union

import cli_ui as ui

from tsrc.errors import LoadManifestSchemaError, MissingRepoError
from tsrc.git_remote import remote_urls_are_same
from tsrc.groups_to_find import GroupsToFind
from tsrc.local_future_manifest import get_local_future_manifests_manifest_and_repos
from tsrc.local_manifest import LocalManifest
from tsrc.manifest import Manifest, RepoNotFound
from tsrc.manifest_common import ManifestGetRepos, ManifestGroupNotFound
from tsrc.manifest_common_data import ManifestsTypeOfData, get_main_color
from tsrc.pcs_repo import PCSRepo
from tsrc.repo import Repo
from tsrc.status_endpoint import Status
from tsrc.utils import align_left, len_of_cli_ui
from tsrc.workspace import Workspace

StatusOrError = Union[Status, Exception]


class WorkspaceReposSummary:
    def __init__(
        self,
        workspace: Workspace,
        gtf: GroupsToFind,
        dm: Union[PCSRepo, None],
        only_manifest: bool = False,
        manifest_marker: bool = True,
        future_manifest: bool = True,
        use_same_future_manifest: bool = False,
    ) -> None:
        self.workspace = workspace
        self.gtf = gtf
        self.dm = dm  # presence is also a marker
        self.is_manifest_marker = manifest_marker
        self.is_future_manifest = future_manifest
        self.use_same_future_manifest = use_same_future_manifest

        # defaults
        self.statuses: Dict[str, StatusOrError] = {}
        self.only_manifest = only_manifest
        # self.apprise: bool = False

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
        self.max_a_block = 0  # apprise block

        # local variables
        self.d_m_root_point = False

        # Groups related
        self.must_find_all_groups = False

        # leftovers related
        self.f_m_repos: Union[List[Repo], None] = None  # for future manifest leftovers
        self.deep_manifest: Union[Manifest, None] = None
        self.d_m_repos: Union[List[Repo], None] = None
        self.local_leftovers: List[str] = []  # leftovers that present localy
        self.leftover_statuses: Dict[str, StatusOrError] = {}
        self._fml_alone_print: bool = False  # Future Manifest leftover - alone print

        # for detection of <something> is empty
        self.d_m_repo_found_some = False
        self.f_m_leftovers_displayed = (
            False  # so FM leftovers will be displayed just once
        )

        # internal markers
        self.is_dry_run: bool = True  # when Workspace is empty

    """General use, publicaly callable"""

    def prepare_repos(self) -> None:
        """
        Obtain every possible data, that can be safely obtained
        before 'process_items' is called

        This is designed to prepare list of leftovers
        (both Deep Manifest's and Future Manifest's),
        that if present, can be added to 'process_items' calculation
        """

        # Future Manifest repos (and max len)
        self.f_m_repos = self._ready_f_m_repos()
        if self.f_m_repos:
            self.max_fm_desc = self._check_max_fm_desc(self.f_m_repos)

        # Deep Manifest repos (and max len)
        self.d_m_repos, self.deep_manifest = self._ready_d_m_repos()
        if self.dm and self.d_m_repos:
            self.max_dm_desc = self._check_max_dm_desc(
                self.dm,
                self.d_m_repos,
            )

    def obtain_leftovers_repos(self, cur_repos: Union[List[Repo], None]) -> List[Repo]:
        """
        if there are leftovers and some of them is present for some reason,
        we may want to add them to the list of GIT status calculation

        if GIT status is not Error, we can use GIT description later
        in the summary output (that is exactly the goal)
        """
        out_repos: List[Repo] = []
        out_repos += self._obtain_leftovers_repos_for_dm(cur_repos)
        next_cur_repos: List[Repo] = []
        if cur_repos:
            next_cur_repos += cur_repos
        if out_repos:
            next_cur_repos += out_repos
        out_repos += self._obtain_leftovers_repos_for_fm(next_cur_repos)

        return out_repos

    def ready_data(
        self,
        statuses: Dict[str, StatusOrError],
    ) -> None:
        """Used to fill the data from statuses
        of Workspace Repos"""
        # provide everything besides 'Workspace'
        self.statuses = statuses

        self.clone_all_repos = False
        if self.workspace.config.clone_all_repos is True:
            self.clone_all_repos = True

    def separate_leftover_statuses(self, repos: Union[List[Repo], None]) -> None:
        """
        once 'process_items' was called and we have GIT statuses,
        we should separate original Workspace Repos Statuses
        and leftovers Repos Statuses, so it does not cause the issues
        later on.

        separated leftovers Repos Statuses should be put to
        'leftover_statuses' and it should have same format as Statuses

        that is what we will do here
        """
        for dest, status in self.statuses.items():
            if self.local_leftovers and dest in self.local_leftovers:
                self.leftover_statuses[dest] = status
        if self.leftover_statuses:
            for l_dest, _ in self.leftover_statuses.items():
                if self.statuses:
                    if l_dest in self.statuses.keys():
                        self.statuses.pop(l_dest)

    def summary(self) -> None:
        """
        Called to print all the reasonable data
        of Workspace, when there are some
        """

        # no need to perform dry run check and calculation
        self.is_dry_run = False

        # side-quest: check Deep Manifest for root point
        if self.deep_manifest and self.dm:
            self.d_m_root_point = self._check_d_m_root_point(
                self.workspace, self.statuses, self.deep_manifest, self.dm.dest
            )

        # alignment for 'dest'
        self.max_dest = self._check_max_dest(self.d_m_repos, self.f_m_repos)

        # get max (current) description
        self.max_desc = self._check_max_desc(self.workspace, self.statuses)

        # calculate max apprise block
        if self.is_future_manifest is True:
            self.max_a_block = self._check_max_a_block()

        # deepcopy before calling 'pop'(s)
        deep_manifest_orig = deepcopy(self.deep_manifest)

        # this should always ensure that items will be sorted by key
        #        has_d_m_d: OrderedDict[str, bool] = self._sort_based_on_d_m(
        #            has_d_m_d, d_m_repos, deep_manifest
        #        )
        has_d_m_d: Dict[str, bool] = self._prepare_for_sort_on_d_m(self.deep_manifest)
        s_has_d_m_d: OrderedDict[str, bool] = self._sort_based_on_d_m(
            has_d_m_d, self.d_m_repos, self.deep_manifest
        )

        # bring original deep_manifest back
        self.deep_manifest = deep_manifest_orig

        # once again prepare for leftovers
        self.d_m_repos = None
        if self.deep_manifest:
            mgr = ManifestGetRepos(
                self.workspace, self.deep_manifest, clone_all_repos=self.clone_all_repos
            )
            self.d_m_repos, self.must_find_all_groups, self.gtf = mgr.by_groups(
                self.gtf, self.must_find_all_groups
            )

        # print main part with current workspace repositories
        self._core_message_print(
            self.deep_manifest,
            s_has_d_m_d,
            self.d_m_repos,
            self.f_m_repos,
        )

    def check_for_leftovers(self) -> None:
        """Used when we do not have Repos
        and statuses from Workspace"""

        # only if normal Summary does not run
        if self.is_dry_run is True:

            # calculate max_dest
            self.max_dest = self._check_max_dest(self.d_m_repos, self.f_m_repos)

            if self.max_dest > 0:
                self._fml_alone_print = True
                self._core_message_header(is_dry=True)

            self.max_desc = self._check_max_desc(self.workspace, self.statuses)

            # calculate max apprise block
            if self.is_future_manifest is True:
                self.max_a_block = self._check_max_a_block()

        if self.max_dest > 0:
            # recollect leftovers only if there is full list
            if self.deep_manifest:
                self._describe_deep_manifest_leftovers(
                    self.workspace,
                    self.deep_manifest,
                    self.d_m_repos,
                    self.f_m_repos,
                )

            # recollect Future Manifest leftovers
            if self.f_m_repos:
                self._describe_future_manifest_leftovers(self.workspace, self.f_m_repos)
        else:
            self._describe_workspace_is_empty()

    """Groups related: check"""

    def must_match_all_groups(self, ignore_if_group_not_found: bool = False) -> None:
        is_all_found, missing_groups = self.gtf.all_found()
        if is_all_found is False:
            for missing_group in missing_groups:
                if ignore_if_group_not_found is True:
                    ui.warning("Missing group:", missing_group)
                else:
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
                    r_repo = deepcopy(m_repo)
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
            else:
                has_d_m_d[dest] = False
        return has_d_m_d

    """Deep Manifest leftovers-only: gathering"""

    def _ready_d_m_repos(
        self,
    ) -> Tuple[Union[List[Repo], None], Union[Manifest, None]]:
        if self.dm:
            path = self.workspace.root_path / self.dm.dest
            ldm = LocalManifest(path)
            try:
                ldmm = ldm.get_manifest_safe_mode(ManifestsTypeOfData.DEEP)
            except LoadManifestSchemaError as lmse:
                ui.warning(lmse)
                self.dm = None  # unset Deep Manifest
                return None, None

            mgr = ManifestGetRepos(
                self.workspace, ldmm, True, self.workspace.config.clone_all_repos
            )

            # get repos that match Groups provided
            repos, self.must_find_all_groups, self.gtf = mgr.by_groups(
                self.gtf, must_find_all_groups=self.must_find_all_groups
            )

            d_m_repos = []
            for repo in repos:
                if self.only_manifest is True:
                    for remote in repo.remotes:
                        if (
                            remote_urls_are_same(
                                self.workspace.config.manifest_url, remote.url
                            )
                            is True
                        ):
                            d_m_repos.append(repo)
                            break
                else:
                    d_m_repos.append(repo)

            if d_m_repos:
                return d_m_repos, ldmm

        return None, None

    def _obtain_leftovers_repos_for_dm(
        self, cur_repos: Union[List[Repo], None]
    ) -> List[Repo]:
        out_repo: List[Repo] = []
        is_found: bool
        if self.d_m_repos:
            for d_repo in self.d_m_repos:
                # check if for Repo there is its directory
                if (self.workspace.root_path / d_repo.dest).is_dir() is False:
                    continue
                is_found = True
                if cur_repos:
                    for cur_repo in cur_repos:
                        if cur_repo.dest == d_repo.dest:
                            is_found = False
                            break
                if is_found is True:
                    out_repo.append(d_repo)
                    self.local_leftovers.append(d_repo.dest)
        return out_repo

    """Future Manifest leftovers-only: gathering"""

    def _ready_f_m_repos(
        self,
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

    def _obtain_leftovers_repos_for_fm(
        self, cur_repos: Union[List[Repo], None]
    ) -> List[Repo]:
        out_repo: List[Repo] = []
        if self.f_m_repos:
            for f_repo in self.f_m_repos:
                if (self.workspace.root_path / f_repo.dest).is_dir() is False:
                    continue
                is_found = True
                if cur_repos:
                    for cur_repo in cur_repos:
                        if cur_repo.dest == f_repo.dest:
                            is_found = False
                            break
                if is_found is True:
                    out_repo.append(f_repo)
                    self.local_leftovers.append(f_repo.dest)
        return out_repo

    """alignment calculations part"""

    def _check_max_dest(
        self, d_m_repos: Union[List[Repo], None], f_m_repos: Union[List[Repo], None]
    ) -> int:
        """
        new: use List[Repo] for both: DM and FM

        consider for max length calculation:
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

        if d_m_repos:
            if self.only_manifest is True:
                m_loop_break: bool = False
                for d_m_repo in d_m_repos:
                    if m_loop_break is True:
                        break
                    for remote in d_m_repo.remotes:
                        if (
                            remote_urls_are_same(
                                self.workspace.config.manifest_url, remote.url
                            )
                            is True
                        ):
                            max_dest_dm = len(d_m_repo.dest)
                            # break both of the loops for optim.
                            m_loop_break = True
                            break
            else:
                max_dest_dm = max(len(x.dest) for x in d_m_repos)

        max_dest_fm = self._check_max_dest_fm_part(f_m_repos)

        return max(max_dest_dm, max_dest, max_dest_fm)

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
                            return repo.len_of_describe()
            else:
                max_dm_desc = max(x.len_of_describe() for x in d_m_repos)
        return max_dm_desc

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

    def _check_max_fm_desc(
        self,
        f_m_repos: Union[List[Repo], None],
    ) -> int:
        max_f_branch = 0
        if f_m_repos:
            max_f_branch = max(x.len_of_describe() for x in f_m_repos)

        return max_f_branch

    def _check_max_desc(
        self,
        workspace: Workspace,
        statuses: Dict[str, StatusOrError],
    ) -> int:
        this_list: List[int] = []
        for _, status in statuses.items():
            if isinstance(status, Status):
                this_list.append(status.git.len_of_describe_branch())
        for _, status in self.leftover_statuses.items():
            if isinstance(status, Status):
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

    def _core_message_header(self, is_dry: bool = False) -> None:
        if self.max_dest > 0:
            if is_dry is True:
                ui.info_2("Only leftovers were found, containing:")
            else:
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
            if isinstance(status, MissingRepoError) or isinstance(status, Exception):
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
            message += [get_main_color(ManifestsTypeOfData.DEEP_BLOCK), "[", ui.green]
            desc, _ = d_m_repo.describe_to_tokens(self.max_dm_desc)
            message += desc
            if sm and dest == sm.dest:
                if self.d_m_root_point is True:
                    message += [
                        get_main_color(ManifestsTypeOfData.DEEP_BLOCK),
                        "]=",
                        ui.reset,
                    ]
                else:
                    message += [
                        get_main_color(ManifestsTypeOfData.DEEP_BLOCK),
                        "]",
                        ui.reset,
                    ]
            else:
                if self.d_m_root_point is True:
                    message += [
                        get_main_color(ManifestsTypeOfData.DEEP_BLOCK),
                        "] ",
                        ui.reset,
                    ]
                else:
                    message += [
                        get_main_color(ManifestsTypeOfData.DEEP_BLOCK),
                        "]",
                        ui.reset,
                    ]
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
        if isinstance(status, MissingRepoError):
            return [ui.red, "error: missing repo"]
        if isinstance(status, Exception):
            return [ui.red, "error: ", status]
        git_status: List[ui.Token] = []
        git_status += status.git.describe_pre_branch()

        if not git_status:
            if self.is_future_manifest is True and self.max_fm_desc > 0:
                if fm_dest_is_empty is True:
                    apprise_repo = None
                git_status += self._describe_status_apprise_part(
                    status.git.describe_branch(),
                    apprise_repo,
                )
            else:
                git_status += status.git.describe_branch()
            git_status += status.git.describe_post_branch()

        manifest_status = status.manifest.describe()
        return git_status + manifest_status

    def _describe_status_apprise_part(
        self,
        desc_tokens: List[ui.Token],
        apprise_repo: Union[Repo, None],
    ) -> List[ui.Token]:
        """usefull for Future Manifest"""
        message: List[ui.Token] = []
        message += [get_main_color(ManifestsTypeOfData.FUTURE)]
        message += ["("]
        if apprise_repo:
            desc, desc_cmp = apprise_repo.describe_to_tokens(
                self.max_fm_desc, ManifestsTypeOfData.FUTURE
            )
            message += desc
            if self._compare_ui_token(desc_cmp, desc_tokens) is True:
                message += [ui.blue, "=="]
            else:
                message += [ui.blue, "<<"]
        else:
            if self.lfm and self.max_fm_desc > 0:
                message += [" ".ljust(self.max_fm_desc), "<<"]
        message += desc_tokens
        message += [get_main_color(ManifestsTypeOfData.FUTURE)]
        message += [")", ui.reset]
        return message

    """describe part: marker"""

    def _describe_on_manifest(
        self,
        tod: ManifestsTypeOfData = ManifestsTypeOfData.LOCAL,
        dest_has_apprise_desc: bool = False,
        consider_align_before: bool = False,
        align_before: int = 0,
    ) -> List[ui.Token]:
        message: List[ui.Token] = []
        message += [get_main_color(tod)]
        l_just = 0

        if tod == ManifestsTypeOfData.DEEP:
            if align_before > 0 and dest_has_apprise_desc is True:
                l_just = align_before + 1
            if dest_has_apprise_desc is False:
                if self.is_future_manifest is True and self.max_fm_desc > 0:
                    if self.max_a_block > 0:
                        l_just = self.max_a_block + 1
                else:
                    if align_before == 0:
                        if consider_align_before is False:
                            l_just = self.max_desc + 1
                    else:
                        l_just = align_before
        else:
            if align_before > 0:
                l_just = align_before + 1

        message += align_left(l_just, "~~ MANIFEST")
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

        message += self._describe_leftover_repo_dest_column(
            leftover, ManifestsTypeOfData.DEEP
        )

        message += self._describe_deep_manifest_leftovers_repo_dm_column(leftover)

        # prepare git description for Repo, if there is one
        gd_message = self._get_desc_of_leftover_statuses(leftover)

        dest_has_apprise_desc: bool = False
        dest_has_apprise_desc_extra: bool = False
        desc_field_is_empty: bool = False
        if self.lfm_repos and f_m_repos:
            _, this_repo = self._repo_found_regardles_branch(
                deep_manifest, leftover, f_m_repos, leftover.dest
            )
            if this_repo:
                # found Future Manifest leftovers in Deep Manifest Leftovers
                if self.is_future_manifest is True:
                    if not gd_message:
                        gd_message = [ui.reset, ":::"]
                        desc_field_is_empty = True
                    message += self._describe_status_apprise_part(
                        # ":::" is one of few not valid branch name,
                        # therefore is suitable to be mark for N/A
                        gd_message,
                        self.lfm_repos[leftover.dest],
                    )
                    dest_has_apprise_desc = True
                self._m_prepare_for_leftovers_regardles_branch(this_repo, f_m_repos)

        if dest_has_apprise_desc is False:

            # check if we should print apprise block anyway
            if self.lfm_repos and gd_message:
                gd_message = self._describe_status_apprise_part(gd_message, None)
                dest_has_apprise_desc = True
                dest_has_apprise_desc_extra = True
            message += gd_message

        if is_manifest_marker is True and is_manifest_marker_displayed is False:
            (
                a_block_len,
                consider_align_before,
            ) = self._dm_leftovers_calculate_align_before(
                gd_message,
                dest_has_apprise_desc,
                dest_has_apprise_desc_extra,
                desc_field_is_empty,
            )

            # add Manifest mark with proper color
            message += self._describe_on_manifest(
                ManifestsTypeOfData.DEEP,
                dest_has_apprise_desc=dest_has_apprise_desc,
                consider_align_before=consider_align_before,
                align_before=a_block_len,
            )
            is_manifest_marker_displayed = True

        ui.info(*message)
        return is_manifest_marker_displayed

    def _dm_leftovers_calculate_align_before(
        self,
        gd_message: List[ui.Token],
        dest_has_apprise_desc: bool,
        dest_has_apprise_desc_extra: bool,
        desc_field_is_empty: bool,
    ) -> Tuple[int, bool]:

        consider_align_before: bool = False
        a_block_len: int = 0
        if gd_message:
            a_block_len = len_of_cli_ui(gd_message) + 1
            if dest_has_apprise_desc is True:
                if desc_field_is_empty is True:
                    a_block_len = self.max_a_block - a_block_len - 3 - self.max_desc - 3
                else:
                    if dest_has_apprise_desc_extra is True:
                        a_block_len = self.max_a_block - a_block_len
                    else:
                        a_block_len = self.max_desc - a_block_len
            else:
                a_block_len = self.max_desc - a_block_len + 1
                consider_align_before = True
        return a_block_len, consider_align_before

    def _get_desc_of_leftover_statuses(self, leftover: Repo) -> List[ui.Token]:
        gd_message: List[ui.Token] = []
        if self.leftover_statuses and leftover.dest in self.leftover_statuses:
            status = self.leftover_statuses[leftover.dest]
            if isinstance(status, Status):
                gd_message = status.git.describe_branch()
        return gd_message

    def _describe_deep_manifest_leftovers_repo_dm_column(
        self, leftover: Repo
    ) -> List[ui.Token]:
        message: List[ui.Token] = []
        message += [get_main_color(ManifestsTypeOfData.DEEP_BLOCK), "["]
        message += [get_main_color(ManifestsTypeOfData.DEEP)]
        desc, _ = leftover.describe_to_tokens(
            self.max_dm_desc, ManifestsTypeOfData.DEEP
        )
        message += desc
        if self.d_m_root_point is True:
            message += [get_main_color(ManifestsTypeOfData.DEEP_BLOCK), "] ", ui.reset]
        else:
            message += [get_main_color(ManifestsTypeOfData.DEEP_BLOCK), "]", ui.reset]
        return message

    def _describe_leftover_repo_dest_column(
        self, leftover: Repo, tod: ManifestsTypeOfData
    ) -> List[ui.Token]:
        message: List[ui.Token] = []
        main_color = get_main_color(tod)
        if (self.workspace.root_path / leftover.dest).is_dir() is True:
            if leftover.dest in self.leftover_statuses:
                status = self.leftover_statuses[leftover.dest]
                if isinstance(status, Status) and status.git.empty is False:
                    message += [ui.green]
                else:
                    message += [ui.reset]
            else:
                message += [ui.reset]
            message += ["+", main_color]
        else:
            message += [ui.reset, "-", main_color]
        message += [leftover.dest.ljust(self.max_dest)]
        return message

    def _describe_future_manifest_leftovers(
        self,
        workspace: Workspace,
        f_m_repos: Union[List[Repo], None],
    ) -> None:
        if self.f_m_leftovers_displayed is True:
            return
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
        message += self._describe_leftover_repo_dest_column(
            leftover, ManifestsTypeOfData.FUTURE
        )

        if self.max_dm_desc > 0:
            message += self._describe_future_manifest_leftovers_empty_space(
                self.max_dm_desc
            )

        # apprise message part
        a_message = self._describe_future_manifest_leftovers_apprise_column(leftover)
        message += a_message

        if self.is_manifest_marker is True and is_future_manifest is True:
            # add Manifest mark with proper color
            a_block_len: int = 0
            if a_message:
                a_block_len = len_of_cli_ui(a_message) + 1

            message += self._describe_on_manifest(
                ManifestsTypeOfData.FUTURE,
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

    def _describe_future_manifest_leftovers_apprise_column(
        self,
        leftover: Repo,
    ) -> List[ui.Token]:
        message: List[ui.Token] = []
        # a_message: List[ui.Token] = []
        if self.is_future_manifest is True:
            # ":::" is one of few not valid branch name,
            # therefore is suitable to be mark for N/A
            gd_message: List[ui.Token] = [ui.reset, ":::"]
            if self.leftover_statuses and leftover.dest in self.leftover_statuses:
                status = self.leftover_statuses[leftover.dest]
                if isinstance(status, Status):
                    gd_message = status.git.describe_branch()
            message = self._describe_status_apprise_part(gd_message, leftover)
        return message

    """describe part: empty"""

    def _describe_workspace_is_empty(self) -> None:
        ui.info_2("Workspace is empty")
