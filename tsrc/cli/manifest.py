""" Entry point for `tsrc manifest`. """
import argparse
from pathlib import Path

import collections
from typing import Dict, List, Optional, Tuple, Union

import cli_ui as ui

from tsrc.cli import (
    add_groups_arg,
    add_num_jobs_arg,
    add_workspace_arg,
    get_num_jobs,
    add_repos_selection_args,
    get_workspace_with_repos,
    repos_from_config,
)
from tsrc.errors import Error
from tsrc.local_manifest import LocalManifest
from tsrc.workspace import Workspace
from tsrc.workspace_config import WorkspaceConfig
from tsrc.executor import Outcome, Task, process_items
from tsrc.repo import Repo
from tsrc.utils import erase_last_line


def configure_parser(subparser: argparse._SubParsersAction) -> None:
    parser = subparser.add_parser("manifest")
    add_workspace_arg(parser)
    add_repos_selection_args(parser)
    parser.add_argument(
        "--branch",
        help="use this branch for the manifest",
        dest="manifest_branch",
    )
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> None:
    workspace = get_workspace_with_repos(args)

    cfg_path = workspace.cfg_path
    manifest_branch = workspace.local_manifest.current_branch()
    workspace_config = workspace.config

    status_collector = StatusCollector(workspace)
    repos = workspace.repos
    process_items(repos, status_collector, num_jobs=1)

    this_dest = None
    this_branch = None
    is_in_workspace = None
    for x in repos:
        this_dest = x.dest
        this_branch = x.branch
        for y in x.remotes:
            if y.url == workspace.config.manifest_url:
                is_in_workspace = True

    ui.info_1("Manifest's URL: ", ui.purple, workspace_config.manifest_url, ui.reset)

    if is_in_workspace:
        ui.info_2("Integrated into Workspace:")
        ui.info(ui.green, "*", ui.reset, this_dest, ui.green, this_branch, ui.reset)

    if args.manifest_branch:
        ui.info_2("Using new branch: ", ui.green, args.manifest_branch, ui.reset)
        workspace_config.manifest_branch = args.manifest_branch
        workspace_config.save_to_file(cfg_path)
        ui.info_1("Workspace updated")
        if is_in_workspace and this_branch != workspace_config.manifest_branch:
            ui.info_2("After sync the branch will", ui.red, "differ", ui.reset)
    else:
        if is_in_workspace and this_branch != workspace_config.manifest_branch:
            ui.info_2("Current branch", ui.red, "(differ):", ui.green, workspace_config.manifest_branch, ui.reset)
        else:
            ui.info_2("Current branch: ", ui.green, workspace_config.manifest_branch, ui.reset)


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
