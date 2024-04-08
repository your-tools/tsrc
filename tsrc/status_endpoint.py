import collections
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import cli_ui as ui

from tsrc.errors import InvalidConfig, MissingRepo
from tsrc.executor import Outcome, Task
from tsrc.git import GitStatus, get_git_status, run_git_captured
from tsrc.manifest import Manifest, RepoNotFound, load_manifest
from tsrc.repo import Repo
from tsrc.static_manifest import StaticManifest, repo_from_static_manifest
from tsrc.utils import erase_last_line
from tsrc.workspace import Workspace


class ManifestStatus:
    """Represent the status of a repo w.r.t the manifest."""

    def __init__(self, repo: Repo, *, manifest: Manifest):
        self.repo = repo
        self.manifest = manifest
        self.incorrect_branch: Optional[Tuple[str, str]] = None
        self.missing_upstream = True

    def update(self, git_status: GitStatus) -> None:
        """Set self.incorrect_branch if the local git status
        does not match the branch set in the manifest.
        """
        expected_branch = self.repo.branch
        actual_branch = git_status.branch
        if actual_branch and actual_branch != expected_branch:
            self.incorrect_branch = (actual_branch, expected_branch)
        self.missing_upstream = not git_status.upstreamed

    def describe(self) -> List[ui.Token]:
        """Return a list of tokens suitable for ui.info()`."""
        res: List[ui.Token] = []
        incorrect_branch = self.incorrect_branch
        if incorrect_branch:
            actual, expected = incorrect_branch
            res += [ui.red, "(expected: " + expected + ")"]
        if self.missing_upstream:
            res += [ui.red, "(missing upstream)"]
        return res


class Status:
    """Wrapper class for both ManifestStatus and GitStatus"""

    def __init__(self, *, git: GitStatus, manifest: ManifestStatus):
        self.git = git
        self.manifest = manifest


class StatusCollector(Task[Repo]):
    """Implement a Task to collect local git status and
    stats w.r.t the manifest for each repo.
    """

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace
        self.manifest = workspace.get_manifest()
        self.statuses: CollectedStatuses = collections.OrderedDict()

    def describe_item(self, item: Repo) -> str:
        return item.dest

    def describe_process_start(self, item: Repo) -> List[ui.Token]:
        return [item.dest]

    def describe_process_end(self, item: Repo) -> List[ui.Token]:
        return []

    def process(self, index: int, count: int, repo: Repo) -> Outcome:
        # Note: Outcome is always empty here, because we
        # use self.statuses in the main `run()` function instead
        # of calling OutcomeCollection.print_summary()
        full_path = self.workspace.root_path / repo.dest
        self.info_count(index, count, repo.dest, end="\r")
        if not full_path.exists():
            self.statuses[repo.dest] = MissingRepo(repo.dest)
        try:
            git_status = get_git_status(full_path)
            manifest_status = ManifestStatus(repo, manifest=self.manifest)
            manifest_status.update(git_status)
            status = Status(git=git_status, manifest=manifest_status)
            self.statuses[repo.dest] = status
        except Exception as e:
            self.statuses[repo.dest] = e
        if not self.parallel:
            erase_last_line()
        return Outcome.empty()


StatusOrError = Union[Status, Exception]
CollectedStatuses = Dict[str, StatusOrError]


class WorkspaceReposSummary:
    def __init__(
        self,
        workspace: Workspace,
        statuses: Dict[str, StatusOrError],
        sm: Union[StaticManifest, None],
        w_c_m_branch: str,
        groups: Union[List[str], None],
        do_update: bool = False,
        only_manifest: bool = False,
    ) -> None:
        self.workspace = workspace
        self.statuses = statuses
        self.sm = sm
        self.w_c_m_branch = w_c_m_branch
        self.groups = groups
        self.do_update = do_update
        self.only_manifest = only_manifest
        # local variables
        self.d_m_root_point = False
        if groups:
            self.all_groups = False
        else:
            self.all_groups = True

        self.clone_all_repos = False
        if self.workspace.config.clone_all_repos is True:
            self.clone_all_repos = True

        # protect agains the case when there is not a single
        # Deep Manifest repository found (for alignment)
        self.d_m_repo_found_some = False

    def summary(self) -> Union[Repo, None]:

        # calculate all Deep_Manifest max branch name length
        # and if Deep_Manifest is found, return it as well
        max_m_branch, deep_manifest = self._max_len_manifest_branch(
            self.workspace,
            self.sm,
            self.statuses,
        )

        max_dest = 0
        if self.only_manifest is False:
            max_dest = self._correct_max_dest(deep_manifest)
        else:
            max_m_branch = 0

        # this should always ensure that items will be sorted by key
        o_stats = collections.OrderedDict(sorted(self.statuses.items()))
        has_d_m_d = collections.OrderedDict()
        for dest in o_stats.keys():
            # following condition is only here to minimize execution
            if self.only_manifest is False or (self.sm and dest == self.sm.dest):
                # produce just [True|False] to be used as key in sorting items
                d_m_repo_found, _ = self._repo_matched_d_m_dest(
                    self.workspace,
                    deep_manifest,
                    dest,
                )
                has_d_m_d[dest] = d_m_repo_found
                if d_m_repo_found is True:
                    self.d_m_repo_found_some = True

        s_has_d_m_d = collections.OrderedDict()

        # sort based on: bool: is there a Deep Manifest corelated repository?
        for key in sorted(has_d_m_d, key=has_d_m_d.__getitem__):
            s_has_d_m_d[key] = has_d_m_d[key]

        # let us now print the full list of all repos
        cur_w_m_repo = None
        if deep_manifest:
            d_m_repos = self._manifest_get_repos(deep_manifest, self.groups)

            # print main part with current workspace repositories
            cur_w_m_repo = self._core_message_print(
                deep_manifest,
                s_has_d_m_d,
                max_dest,
                max_m_branch,
                d_m_repos,
            )

            # recollect leftovers only if there is full list
            if self.only_manifest is False:
                self._describe_deep_manifest_leftovers(
                    d_m_repos,
                    max_dest,
                    max_m_branch,
                )

            # if we did not found current Workspace Manifest repo,
            # create and assign one from Workspace configuration
            if self.sm and not cur_w_m_repo:
                cur_w_st_m = StaticManifest(
                    dest=self.sm.dest,
                    branch=self.sm.branch,
                    url=self.workspace.config.manifest_url,
                )
                cur_w_m_repo = repo_from_static_manifest(cur_w_st_m)
        else:
            # print just current workspace repositories and nothing else
            self._core_message_print(
                deep_manifest,
                s_has_d_m_d,
                max_dest,
                max_m_branch,
            )

        return cur_w_m_repo

    def _core_message_print(
        self,
        deep_manifest: Union[Manifest, None],
        s_has_d_m_d: collections.OrderedDict,
        max_dest: int,
        max_m_branch: int,
        d_m_repos: Union[List[Repo], None] = None,
    ) -> Union[Repo, None]:
        """Prints a summary of Workspace repository status.

        How to understand the output:
        * repository path (default color)
        * [ branch_of_Manifest_repository_from_manifest.yml ]=
        (represents some kind of inside block as if Manifest expands)
        * current branch (and description) from workspace point of view
        * <—— MANIFEST: (purple) (for Manifest repo only)
        (represents pointer)
        * manifest branch from last 'sync'
        * ~~> (default color) (represents transition)
        * newly configured manifest branch (if there is such)
        """
        cur_w_m_repo = None
        for dest in s_has_d_m_d.keys():

            status = self.statuses[dest]
            d_m_repo_found = False
            d_m_repo = None
            # following condition is only here to minimize execution
            if self.only_manifest is False or (self.sm and dest == self.sm.dest):
                d_m_repo_found, d_m_repo = self._repo_matched_d_m_dest(
                    self.workspace,
                    deep_manifest,
                    dest,
                )

            if self.sm and dest == self.sm.dest:
                if self.do_update and self.only_manifest is True:
                    ui.info_2("New state after Workspace update:")
                if isinstance(status, Status):
                    cur_w_m_repo = d_m_repo
            else:
                if self.only_manifest is True:
                    continue

            message = [ui.green, "*", ui.reset, dest.ljust(max_dest)]

            if deep_manifest and self.d_m_repo_found_some is True:
                # get Deep Manifest repo branch
                d_m_repo_branch = self._d_m_prepare_for_leftovers(
                    d_m_repo,
                    d_m_repos,
                )
                # so there can be a nice formated printout
                message += self._describe_deep_manifest(
                    d_m_repo_found,
                    d_m_repo_branch,
                    dest,
                    self.sm,
                    max_m_branch,
                )

            message += self._describe_status(status)

            # final Manifest-only extra markings
            if self.sm and dest == self.sm.dest:
                message += self._describe_on_manifest_repo_status(
                    self.sm.branch, self.w_c_m_branch
                )

            ui.info(*message)

        return cur_w_m_repo

    """common helpers"""

    def _manifest_get_repos(
        self,
        manifest: Manifest,
        groups: Union[List[str], None],
    ) -> List[Repo]:
        found_groups = None
        found_all_groups = True
        if manifest.group_list and groups:
            found_groups = list(set(groups).intersection(manifest.group_list.groups))
            if groups:
                found_all_groups = False
        if self.clone_all_repos is False:
            found_all_groups = False

        return manifest.get_repos(groups=found_groups, all_=found_all_groups)

    def _compare_repo_regardles_branch(
        self,
        repo: Repo,
        in_repo: List[Repo],
    ) -> bool:
        for i in in_repo:
            if i.dest == repo.dest:
                for this_remote in repo.remotes:
                    if this_remote in i.remotes:
                        return True
        return False

    """Deep Manifest related checks"""

    def _repo_matched_d_m_dest(
        self,
        workspace: Workspace,
        deep_manifest: Union[Manifest, None],
        dest: str,
    ) -> Tuple[bool, Union[Repo, None]]:
        """checks if repo on given 'dest'
        matches the repo in Deep Manifest"""
        d_m_repo = None
        if not deep_manifest:
            return False, None
        try:
            d_m_repo = deep_manifest.get_repo(dest)
        except RepoNotFound:
            return False, None

        # we have to make sure provided 'groups' does match Deep Manifest
        d_m_repos = self._manifest_get_repos(deep_manifest, self.groups)
        if not d_m_repos:
            return False, None

        # to proclaiming 'same repo' we have to have:
        # * found in Deep Manifest filtered by groups
        # * (!) ignore Deep Manifest repo branch
        # * same destination,
        # * same remote found as in local_manifest
        # * (!) branch does not have to be the same
        if d_m_repo:
            this_manifest = workspace.local_manifest.get_manifest()
            if (
                self._d_m_repo_is_same_regardles_branch(
                    this_manifest, d_m_repo, d_m_repos, dest
                )
                is True
            ):
                return True, d_m_repo
        return False, None

    def _d_m_repo_is_same_regardles_branch(
        self,
        this_manifest: Manifest,
        d_m_repo: Repo,
        d_m_repos: List[Repo],
        dest: str,
    ) -> bool:
        repos = self._manifest_get_repos(this_manifest, self.groups)
        for repo in repos:
            if self._compare_repo_regardles_branch(repo, d_m_repos) is True:
                if repo.dest == dest:
                    for r_remote in repo.remotes:
                        if r_remote in d_m_repo.remotes:
                            return True
        return False

    def _d_m_prepare_for_leftovers(
        self,
        d_m_repo: Union[Repo, None],
        d_m_repos: Union[List[Repo], None],
    ) -> Union[str, None]:
        """leftover = a (Repo) record in current Deep Manifest
        that is not present in the workspace"""
        d_m_repo_branch = None
        if d_m_repo:
            d_m_repo_branch = d_m_repo.branch
            if d_m_repos and d_m_repo in d_m_repos:
                d_m_repos.pop(d_m_repos.index(d_m_repo))
        return d_m_repo_branch

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
                # check if '[ .. ]=' should be displayed
                d_m_root_point, _ = self._repo_matched_d_m_dest(workspace, d_m, dest)
                return d_m_root_point
        return False

    """length calculations part"""

    def _correct_max_dest(self, deep_manifest: Union[Manifest, None]) -> int:
        """includes Deep Manifest destination names into the max length calculation"""
        max_dest = max(len(x) for x in self.statuses.keys())
        max_dest_dm = 0
        if deep_manifest:
            d_m_repos = self._manifest_get_repos(deep_manifest, self.groups)
            if d_m_repos:
                max_dest_dm = max(len(x.dest) for x in d_m_repos)
        return max(max_dest_dm, max_dest)

    def _max_len_manifest_branch(
        self,
        workspace: Workspace,
        sm: Union[StaticManifest, None],
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
            d_m_repos = self._manifest_get_repos(d_m, self.groups)
            if d_m_repos:
                max_m_branch = max(len(x.branch) for x in d_m_repos)

        return max_m_branch, d_m

    """describe part"""

    def _describe_deep_manifest(
        self,
        d_m_r_found: bool,
        d_m_branch: Union[str, None],
        dest: str,
        sm: Union[StaticManifest, None],
        max_m_branch: int,
    ) -> List[ui.Token]:
        message = []
        if d_m_r_found is True and isinstance(d_m_branch, str):
            message += [ui.brown, "[", ui.green]
            message += [d_m_branch.ljust(max_m_branch)]
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
                    message += [" ".ljust(max_m_branch + 2 + 2 + 1)]
                else:
                    message += [" ".ljust(max_m_branch + 2 + 2)]
        return message

    def _describe_status(self, status: StatusOrError) -> List[ui.Token]:
        """Return a list of tokens suitable for ui.info()."""
        if isinstance(status, MissingRepo):
            return [ui.red, "error: missing repo"]
        if isinstance(status, Exception):
            return [ui.red, "error: ", status]
        git_status = status.git.describe()
        manifest_status = status.manifest.describe()
        return git_status + manifest_status

    def _describe_deep_manifest_leftovers(
        self, d_m_repos: List[Repo], max_dest: int, max_m_branch: int
    ) -> None:
        for leftover in d_m_repos:
            message = [ui.reset, "*", ui.purple, leftover.dest.ljust(max_dest)]
            message += [ui.brown, "[", ui.purple]
            message += [leftover.branch.ljust(max_m_branch)]
            message += [ui.brown, "]", ui.reset]
            ui.info(*message)

    def _describe_on_manifest_repo_status(
        self, s_branch: Union[str, None], c_branch: str
    ) -> List[ui.Token]:
        # exactly on Manifest repository integrated into Workspace
        message = [ui.purple, "<——{ MANIFEST }"]
        if s_branch:
            message += [ui.green, s_branch]
            if c_branch and c_branch != s_branch:
                message += [
                    ui.reset,
                    "~~>",
                    ui.green,
                    c_branch,
                ]
        return message


def is_manifest_in_workspace(
    workspace: Workspace,
    repos: List[Repo],
) -> Union[StaticManifest, None]:
    for x in repos:
        this_dest = x.dest
        this_branch = x.branch
        for y in x.remotes:
            if y.url and y.url == workspace.config.manifest_url:
                # go with 1st one found
                return StaticManifest(
                    this_dest, this_branch, url=workspace.config.manifest_url
                )
    return None


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


def describe_status(status: StatusOrError) -> List[ui.Token]:
    """Return a list of tokens suitable for ui.info()."""
    if isinstance(status, MissingRepo):
        return [ui.red, "error: missing repo"]
    if isinstance(status, Exception):
        return [ui.red, "error: ", status]
    git_status = status.git.describe()
    manifest_status = status.manifest.describe()
    return git_status + manifest_status
