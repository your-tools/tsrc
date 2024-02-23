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
from tsrc.status_endpoint import ManifestStatus, StatusCollector, describe_status
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
