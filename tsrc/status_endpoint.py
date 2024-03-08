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


def workspace_repositories_summary(
    workspace_root_path: Path,
    statuses: Dict[str, StatusOrError],
    st_m_m_dest: Union[str, None],
    st_m_m_branch: Union[str, None],
    w_c_m_branch: str,
    do_update: bool = False,
    only_manifest: bool = False,
) -> Union[str, None]:
    """prints a summary of Manifest repository status.
    the same output should be used when using 'tsrc status'
    but with other repositories included

    Few points to output:
    * repository path (default color)
    * [ effective_branch_of_Manifest_repository_from_manifest.yml ]=
    (should represent some kind of inside block as if Manifest expands)
    * current branch from workspace point of view
    * status descriptions
    * <—— MANIFEST: (purple) (should represent pointer)
    * manifest branch from last 'sync'
    * ~~> (default color) (should represent transition)
    * newly configured manifest branch (if there is such)
    """
    deep_manifest = None
    max_m_branch, deep_manifest = max_len_manifest_branch(
        workspace_root_path,
        st_m_m_dest,
        statuses,
    )

    cur_w_m_r_branch = None
    max_dest = 0
    if only_manifest is False:
        max_dest = max(len(x) for x in statuses.keys())
    else:
        max_m_branch = 0

    for dest, status in statuses.items():
        d_m_repo_found, d_m_branch = check_if_deep_manifest_repo_dest(
            deep_manifest,
            dest,
        )

        if dest == st_m_m_dest:
            if do_update:
                ui.info_2("New state after Workspace update:")
            if isinstance(status, Status):
                cur_w_m_r_branch = status.git.branch
        else:
            if only_manifest is True:
                continue

        message = [ui.green, "*", ui.reset, dest.ljust(max_dest)]

        if deep_manifest:
            message += deep_manifest_describe(
                d_m_repo_found,
                d_m_branch,
                dest,
                st_m_m_dest,
                max_m_branch,
            )

        message += describe_status(status)

        if dest == st_m_m_dest:
            message += describe_on_manifest_repo_status(st_m_m_branch, w_c_m_branch)

        ui.info(*message)

    return cur_w_m_r_branch


def check_if_deep_manifest_repo_dest(
    deep_manifest: Union[Manifest, None],
    dest: str,
) -> Tuple[bool, Union[str, None]]:
    d_m_repo_found = True
    d_m_branch = None
    if not deep_manifest:
        return False, None
    try:
        d_m_branch = deep_manifest.get_repo(dest).branch
    except RepoNotFound:
        d_m_repo_found = False
    return d_m_repo_found, d_m_branch


def deep_manifest_describe(
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
    w_r_path: Path, st_m_m_dest: Union[str, None], statuses: Dict[str, StatusOrError]
) -> Tuple[int, Union[Manifest, None]]:
    """calculate maximum lenght for deep manifest branch (if present)"""
    max_m_branch = 0
    d_m = None
    if st_m_m_dest:
        d_m = load_manifest(w_r_path / st_m_m_dest / "manifest.yml")
        all_m_branch_len = []
        for dest, _status in statuses.items():
            try:
                this_len = len(d_m.get_repo(dest).branch)
            except RepoNotFound:
                continue
            if dest == st_m_m_dest:
                this_len = this_len + 1
            all_m_branch_len += [this_len]
        max_m_branch = max(all_m_branch_len)
    return max_m_branch, d_m


def describe_on_manifest_repo_status(
    s_branch: Union[str, None], c_branch: str
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


def describe_status(status: StatusOrError) -> List[ui.Token]:
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
    rc, l_m_sha = run_git_captured(
        w_r_path / dest,
        "rev-parse",
        "--verify",
        "HEAD",
        check=False,
    )
    if rc != 0:
        return None, None

    tmp_ref = "{}@{{upstream}}"
    rc, this_ref = run_git_captured(
        w_r_path / dest,
        "rev-parse",
        "--symbolic-full-name",
        "--abbrev-ref",
        tmp_ref.format(branch),
        check=False,
    )
    r_m_sha = None
    if rc == 0:
        tmp_r_ref = this_ref.split("/")
        this_remote = tmp_r_ref[0]
        this_r_ref = "refs/heads/" + tmp_r_ref[1]
        _, r_m_sha = run_git_captured(
            w_r_path / dest,
            "ls-remote",
            "--exit-code",
            "--head",
            this_remote,
            this_r_ref,
            check=True,
        )
    if r_m_sha:
        return l_m_sha, r_m_sha.split()[0]
    else:
        return l_m_sha, None
