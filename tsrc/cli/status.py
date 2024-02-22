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
from tsrc.git import GitStatus, get_git_status, run_git_captured
from tsrc.manifest import Manifest
from tsrc.repo import Repo
from tsrc.utils import erase_last_line
from tsrc.workspace import Workspace
from tsrc.status_endpoint import StatusCollector, ManifestStatus, describe_status


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

    """detect same Manifest's repository in the workspace repositories"""
    """and also check if there is missing upstream"""
    static_manifest_manifest_dest = None    # "static" as it cannot be changed, "manifest_manifest" = Manifest repo in Manifest.yml; this may not exist but if it does, it will be the 'dest'intion == "direcory_name"
    static_manifest_manifest_branch = None  # "static" as it cannot be changed, "manifest_manifest" = Manifest repo in Manifest.yml; this may not exist, but if it does, it will be the (git) 'branch'
    workspace_manifest_repo_branch = None   # Workspace's > Manifest_repo's > branch
    for x in repos:
        this_dest = x.dest
        this_branch = x.branch
        for y in x.remotes:
            if y.url == workspace.config.manifest_url:
                static_manifest_manifest_dest = this_dest
                workspace_manifest_repo_branch = workspace.local_manifest.current_branch()
                static_manifest_manifest_branch = this_branch

    max_dest = max(len(x) for x in statuses.keys())
    for dest, status in statuses.items():
        message = [ui.green, "*", ui.reset, dest.ljust(max_dest)]
        message += describe_status(status)
        if dest == static_manifest_manifest_dest:
            message += [ui.purple, "<---", "MANIFEST:"]
            message += [ui.green, static_manifest_manifest_branch]
            if workspace.config.manifest_branch != static_manifest_manifest_branch:
                message += [ui.reset, "~~~>", ui.green, workspace.config.manifest_branch]
        ui.info(*message)

