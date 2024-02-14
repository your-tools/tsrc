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
from tsrc.git import run_git_captured


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

    this_manifest_dest = None
    this_manifest_branch = None
    manifest_is_in_workspace = False
    for x in repos:
        for y in x.remotes:
            if y.url == workspace.config.manifest_url:
                manifest_is_in_workspace = True
                this_manifest_dest = x.dest
                this_manifest_branch = x.branch


    ui.info_1("Manifest's URL: ", ui.purple, workspace_config.manifest_url, ui.reset)

    if manifest_is_in_workspace:
        ui.info_2("Integrated into Workspace:")
        ui.info(ui.green, "*", ui.reset, this_manifest_dest, ui.green, this_manifest_branch, ui.reset)

    if args.manifest_branch:
        """ first we need to check if such branch exists in order this to work on 'sync' """
        vrf_tmp_ref = "{}@{{upstream}}"
        rc_is_on_remote, _ = run_git_captured(workspace.root_path / this_manifest_dest, "rev-parse", "--symbolic-full-name", "--abbrev-ref", f"{args.manifest_branch}@{{upstream}}", check=False)
        if rc_is_on_remote != 0:
            """ we have not found remote branch. is there at least local one? """
            if manifest_is_in_workspace:
                found_local_branch = False
                _, full_list_of_branches = run_git_captured(workspace.root_path / this_manifest_dest, "branch", '--format="%(refname:short)"', check=False)
                for line in full_list_of_branches.splitlines():
                    if line.startswith('"' + args.manifest_branch + '"'):
                        found_local_branch = True
                        break

        if rc_is_on_remote == 0 or found_local_branch:
            """ we are good to set new branch """
            ui.info_2("Using new branch: ", ui.green, args.manifest_branch, ui.reset)
            workspace_config.manifest_branch = args.manifest_branch
            workspace_config.save_to_file(cfg_path)
            ui.info_1("Workspace updated")
            if manifest_is_in_workspace:
                if rc_is_on_remote == 0:
                    if this_manifest_branch != workspace_config.manifest_branch:
                        ui.info_2("After sync the branch will", ui.red, "differ", ui.reset)
                else:
                    ui.info_2("You need to", ui.red, "'git push'", ui.reset, "this branch to remote in order", ui.blue, "'sync'", ui.reset, "to work")
        else:
            ui.error(f"Cannot use '{args.manifest_branch}' as new branch as it does not exist. You need to create it first.")
    else:
        if manifest_is_in_workspace and this_manifest_branch != workspace_config.manifest_branch:
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
