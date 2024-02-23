""" Entry point for tsrc status """

import argparse
import collections
from typing import Dict, List, Optional, Tuple, Union

import cli_ui as ui

from tsrc.cli import (
    add_num_jobs_arg,
    add_repos_selection_args,
    add_workspace_arg,
    get_num_jobs,
    get_workspace_with_repos,
)
from tsrc.errors import MissingRepo
from tsrc.executor import Outcome, Task, process_items
from tsrc.git import GitStatus, get_git_status
from tsrc.manifest import Manifest
from tsrc.repo import Repo
from tsrc.utils import erase_last_line
from tsrc.workspace import Workspace


def configure_parser(subparser: argparse._SubParsersAction) -> None:
    parser = subparser.add_parser("status")
    add_workspace_arg(parser)
    add_repos_selection_args(parser)
    add_num_jobs_arg(parser)
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> None:
    workspace = get_workspace_with_repos(args)
    status_collector = StatusCollector(workspace)
    repos = workspace.repos
    if not repos:
        ui.info_2("Workspace is empty")
        return
    ui.info_1(f"Collecting statuses of {len(repos)} repo(s)")
    num_jobs = get_num_jobs(args)
    process_items(repos, status_collector, num_jobs=num_jobs)
    erase_last_line()
    ui.info_2("Workspace status:")
    statuses = status_collector.statuses
    max_dest = max(len(x) for x in statuses.keys())
    for dest, status in statuses.items():
        message = [ui.green, "*", ui.reset, dest.ljust(max_dest)]
        message += describe_status(status)
        ui.info(*message)


class ManifestStatus:
    """Represent the status of a repo w.r.t the manifest."""

    def __init__(self, repo: Repo, *, manifest: Manifest):
        self.repo = repo
        self.manifest = manifest
        self.incorrect_branch: Optional[Tuple[str, str]] = None

    def update(self, git_status: GitStatus) -> None:
        """Set self.incorrect_branch if the local git status
        does not match the branch set in the manifest.
        """
        expected_branch = self.repo.branch
        actual_branch = git_status.branch
        if actual_branch and actual_branch != expected_branch:
            self.incorrect_branch = (actual_branch, expected_branch)

    def describe(self) -> List[ui.Token]:
        """Return a list of tokens suitable for ui.info()`."""
        res: List[ui.Token] = []
        incorrect_branch = self.incorrect_branch
        if incorrect_branch:
            actual, expected = incorrect_branch
            res += [ui.red, "(expected: " + expected + ")"]
        return res


class Status:
    """Wrapper class for both ManifestStatus and GitStatus"""

    def __init__(self, *, git: GitStatus, manifest: ManifestStatus):
        self.git = git
        self.manifest = manifest


StatusOrError = Union[Status, Exception]
CollectedStatuses = Dict[str, StatusOrError]


def describe_status(status: StatusOrError) -> List[ui.Token]:
    """Return a list of tokens suitable for ui.info()."""
    if isinstance(status, MissingRepo):
        return [ui.red, "error: missing repo"]
    if isinstance(status, Exception):
        return [ui.red, "error: ", status]
    git_status = status.git.describe()
    manifest_status = status.manifest.describe()
    return git_status + manifest_status


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
