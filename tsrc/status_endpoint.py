import collections
from typing import Dict, List, Optional, Tuple, Union

import cli_ui as ui

from tsrc.errors import MissingRepoError
from tsrc.executor import Outcome, Task
from tsrc.git import GitStatus, get_git_status
from tsrc.git_remote import GitRemote, get_git_remotes
from tsrc.manifest import Manifest
from tsrc.manifest_common_data import ManifestsTypeOfData
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
        self.git_remote: Union[GitRemote, None] = None

    def update(self, git_status: GitStatus, git_remote: Union[GitRemote, None]) -> None:
        """Set self.incorrect_branch if the local git status
        does not match the branch set in the manifest.
        """
        expected_branch = self.repo.branch
        actual_branch = git_status.branch
        if actual_branch and expected_branch and actual_branch != expected_branch:
            self.incorrect_branch = (actual_branch, expected_branch)
        if git_remote:
            self.missing_upstream = not git_remote.upstreamed
            self.git_remote = git_remote

    def describe(self) -> List[ui.Token]:
        """Return a list of tokens suitable for ui.info()`."""
        res: List[ui.Token] = []
        incorrect_branch = self.incorrect_branch
        if incorrect_branch:
            actual, expected = incorrect_branch
            res += [ui.red, "(expected: " + expected + ")"]
        if self.git_remote and not self.git_remote.remotes:
            res += [ui.red, "(missing remote)"]
        elif self.missing_upstream:
            res += [ui.red, "(missing upstream)"]
        return res


class Status:
    """Wrapper class for both ManifestStatus and GitStatus"""

    def __init__(
        self,
        *,
        git: GitStatus,
        git_remote: Union[GitRemote, None],
        manifest: ManifestStatus
    ):
        self.git = git
        self.git_remote = git_remote
        self.manifest = manifest


class StatusCollector(Task[Repo]):
    """Implement a Task to collect local git status and
    stats w.r.t the manifest for each repo.
    """

    def __init__(self, workspace: Workspace, ignore_group_item: bool = False) -> None:
        self.workspace = workspace
        if ignore_group_item is True:
            self.manifest = workspace.get_manifest_safe_mode(ManifestsTypeOfData.LOCAL)
        else:
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
            self.statuses[repo.dest] = MissingRepoError(repo.dest)
        try:
            git_status = get_git_status(full_path)
            git_remote: Union[GitRemote, None] = None
            if git_status.branch:
                git_remote = get_git_remotes(full_path, git_status.branch)
            manifest_status = ManifestStatus(repo, manifest=self.manifest)
            manifest_status.update(git_status, git_remote)
            status = Status(
                git=git_status, git_remote=git_remote, manifest=manifest_status
            )
            self.statuses[repo.dest] = status
        except Exception as e:
            self.statuses[repo.dest] = e
        if not self.parallel:
            erase_last_line()
        return Outcome.empty()


class StatusCollectorLocalOnly(Task[Repo]):
    """Implement a Task to collect local git status and
    stats w.r.t the manifest for each repo.
    Only considering local properties of Repo.
    This is meant to speed up processing as checking all remotes
    can be time consuming.
    """

    def __init__(self, workspace: Workspace, ignore_group_item: bool = False) -> None:
        self.workspace = workspace
        if ignore_group_item is True:
            self.manifest = workspace.get_manifest_safe_mode(ManifestsTypeOfData.LOCAL)
        else:
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
            self.statuses[repo.dest] = MissingRepoError(repo.dest)
        try:
            git_status = get_git_status(full_path)
            manifest_status = ManifestStatus(repo, manifest=self.manifest)
            manifest_status.update(git_status, None)
            status = Status(git=git_status, git_remote=None, manifest=manifest_status)
            self.statuses[repo.dest] = status
        except Exception as e:
            self.statuses[repo.dest] = e
        if not self.parallel:
            erase_last_line()
        return Outcome.empty()


StatusOrError = Union[Status, Exception]
CollectedStatuses = Dict[str, StatusOrError]
