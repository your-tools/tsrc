import collections
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import cli_ui as ui

from tsrc.errors import MissingRepo
from tsrc.executor import Outcome, Task
from tsrc.git import GitStatus, get_git_status, run_git_captured
from tsrc.manifest import Manifest, RepoNotFound, load_manifest
from tsrc.repo import Repo
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
        workspace_root_path: Path,
        statuses: Dict[str, StatusOrError],
        st_m_m_dest: Union[str, None],
        st_m_m_branch: Union[str, None],
        # TODO: check: should not be also here 'None'?
        w_c_m_branch: str,
        do_update: bool = False,
        only_manifest: bool = False,
    ):
        self.w_r_path = workspace_root_path
        self.statuses = statuses
        self.st_m_m_dest = st_m_m_dest
        self.st_m_m_branch = st_m_m_branch
        self.w_c_m_branch = w_c_m_branch
        self.do_update = do_update
        self.only_manifest = only_manifest

    def summary(self) -> Union[Repo, None]:

        deep_manifest = None
        max_m_branch, deep_manifest = self.max_len_manifest_branch(
            self.w_r_path,
            self.st_m_m_dest,
            self.statuses,
        )

        max_dest = 0
        if self.only_manifest is False:
            max_dest = max(len(x) for x in self.statuses.keys())
        else:
            max_m_branch = 0

        # this shoud ensure always sorted items by key
        o_stats = collections.OrderedDict(sorted(self.statuses.items()))
        has_d_m_d = collections.OrderedDict()
        for dest in o_stats.keys():
            d_m_repo_found, _ = self.check_if_deep_manifest_repo_dest(
                deep_manifest,
                dest,
            )
            has_d_m_d[dest] = d_m_repo_found
        s_has_d_m_d = collections.OrderedDict()

        # sort base on if there is a deep manifest destination
        for key in sorted(has_d_m_d, key=has_d_m_d.__getitem__):
            s_has_d_m_d[key] = has_d_m_d[key]

        # let us print the final list of repos
        cur_w_m_repo = None
        if deep_manifest:
            # prepare to take care of letfovers from deep_manifest
            d_m_repos = deep_manifest.get_repos()

            cur_w_m_repo = self.core_message_print(
                deep_manifest,
                s_has_d_m_d,
                max_dest,
                max_m_branch,
                d_m_repos,
            )

            if self.only_manifest is False:
                # recollect leftovers only if there is full list
                for leftover in d_m_repos:
                    # print("DEBUG repos: dest:", i.dest, "  branch: ", i.branch)
                    message = [ui.reset, "*", ui.purple, dest.ljust(max_dest)]
                    message += [ui.brown, "[", ui.purple]
                    message += [leftover.branch.ljust(max_m_branch)]
                    message += [ui.brown, "]", ui.reset]
                    ui.info(*message)

        return cur_w_m_repo

    def core_message_print(
        self,
        deep_manifest: Manifest,
        s_has_d_m_d: collections.OrderedDict,
        max_dest: int,
        max_m_branch: int,
        d_m_repos: List[Repo],
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
            d_m_repo_found, d_m_repo = self.check_if_deep_manifest_repo_dest(
                deep_manifest,
                dest,
            )

            if dest == self.st_m_m_dest:
                if self.do_update and self.only_manifest is True:
                    ui.info_2("New state after Workspace update:")
                if isinstance(status, Status):
                    cur_w_m_repo = d_m_repo
            else:
                if self.only_manifest is True:
                    continue

            message = [ui.green, "*", ui.reset, dest.ljust(max_dest)]

            if deep_manifest:
                d_m_repo_branch = None
                if d_m_repo:
                    d_m_repo_branch = d_m_repo.branch
                    d_m_repos.pop(d_m_repos.index(d_m_repo))
                message += self.deep_manifest_describe(
                    d_m_repo_found,
                    d_m_repo_branch,
                    dest,
                    self.st_m_m_dest,
                    max_m_branch,
                )

            message += self.describe_status(status)

            if dest == self.st_m_m_dest:
                message += self.describe_on_manifest_repo_status(
                    self.st_m_m_branch, self.w_c_m_branch
                )

            ui.info(*message)

        return cur_w_m_repo

    def check_if_deep_manifest_repo_dest(
        self,
        deep_manifest: Union[Manifest, None],
        dest: str,
    ) -> Tuple[bool, Union[Repo, None]]:
        d_m_repo_found = True
        d_m_repo = None
        if not deep_manifest:
            return False, None
        try:
            d_m_repo = deep_manifest.get_repo(dest)
        except RepoNotFound:
            d_m_repo_found = False
        return d_m_repo_found, d_m_repo

    def deep_manifest_describe(
        self,
        d_m_r_found: bool,
        d_m_branch: Union[str, None],
        dest: str,
        st_m_m_dest: Union[str, None],
        max_m_branch: int,
    ) -> List[ui.Token]:
        message = []
        if d_m_r_found is True and isinstance(d_m_branch, str):
            message += [ui.brown, "[", ui.green]
            message += [d_m_branch.ljust(max_m_branch)]
            if dest == st_m_m_dest:
                message += [ui.brown, "]=", ui.reset]
            else:
                message += [ui.brown, "] ", ui.reset]
        else:
            message += [" ".ljust(max_m_branch + 2 + 2 + 1)]
        return message

    def max_len_manifest_branch(
        self,
        w_r_path: Path,
        st_m_m_dest: Union[str, None],
        statuses: Dict[str, StatusOrError],
    ) -> Tuple[int, Union[Manifest, None]]:
        """calculate maximum lenght for deep manifest branch (if present)"""
        max_m_branch = 0
        d_m = None
        if st_m_m_dest:
            d_m = load_manifest(w_r_path / st_m_m_dest / "manifest.yml")
            all_m_branch_len = []
            for dest, _status in statuses.items():
                """test if such repo exists first before checking it in the deep manifest"""
                try:
                    this_len = len(d_m.get_repo(dest).branch)
                except RepoNotFound:
                    continue
                if dest == st_m_m_dest:
                    this_len = this_len + 1
                all_m_branch_len += [this_len]
            max_m_branch = max(all_m_branch_len)
            max_m_all = 0
            if d_m:
                d_m_stats = d_m.get_repos()
                max_m_all = max(len(x.branch) for x in d_m_stats)
            max_m_branch = max(max_m_branch, max_m_all)
        return max_m_branch, d_m

    def describe_on_manifest_repo_status(
        self, s_branch: Union[str, None], c_branch: str
    ) -> List[ui.Token]:
        """When exactly on Manifest repository integrated into Workspace"""
        message = [ui.purple, "<——", "MANIFEST:"]
        message += [ui.green, s_branch]
        if c_branch != s_branch:
            message += [
                ui.reset,
                "~~>",
                ui.green,
                c_branch,
            ]
        return message

    def describe_status(self, status: StatusOrError) -> List[ui.Token]:
        """Return a list of tokens suitable for ui.info()."""
        if isinstance(status, MissingRepo):
            return [ui.red, "error: missing repo"]
        if isinstance(status, Exception):
            return [ui.red, "error: ", status]
        git_status = status.git.describe()
        manifest_status = status.manifest.describe()
        return git_status + manifest_status


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
