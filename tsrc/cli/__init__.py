""" Common tools for tsrc commands. """

import argparse
import os
import re
import sys
from multiprocessing import cpu_count
from pathlib import Path
from typing import List, Optional

import cli_ui as ui

from tsrc.errors import Error
from tsrc.groups_and_constraints_data import GroupsAndConstraints
from tsrc.manifest import Manifest
from tsrc.manifest_common_data import ManifestsTypeOfData
from tsrc.repo import Repo
from tsrc.workspace import Workspace
from tsrc.workspace_config import WorkspaceConfig


def add_workspace_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-w",
        "--workspace",
        help="workspace path",
        type=Path,
        dest="workspace_path",
    )


def add_num_jobs_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-j",
        "--jobs",
        dest="num_jobs",
        help="Number of jobs to use simultaneously. "
        "Use 1 to disable parallelism. "
        "Defaults to the value of the "
        "TSRC_PARALLEL_JOBS environment variable",
    )


def get_num_jobs(args: argparse.Namespace) -> int:
    from_command_line = args.num_jobs
    from_env = os.environ.get("TSRC_PARALLEL_JOBS")
    if from_command_line:
        value = from_command_line
    else:
        value = from_env
    if value in [None, "auto"]:
        return cpu_count()
    try:
        return int(value)
    except ValueError:
        sys.exit(f"error: argument -j/--jobs: invalid value: {value}")


def get_workspace(namespace: argparse.Namespace, silent: bool = False) -> Workspace:
    workspace_path = namespace.workspace_path or find_workspace_path()
    if silent is False:
        ui.info_1("Using workspace in", ui.bold, workspace_path)
    return Workspace(workspace_path)


def add_groups_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-g", "--group", "--groups", nargs="+", dest="groups", help="groups to use"
    )


def add_repos_selection_args(parser: argparse.ArgumentParser) -> None:
    add_groups_arg(parser)
    parser.add_argument(
        "--all-cloned",
        action="store_true",
        dest="all_cloned",
        help="run on all cloned repos",
    )
    parser.add_argument(
        "-i",
        dest="include_regex",
        help="Include only repositories matching the regex",
    )
    parser.add_argument(
        "-e", dest="exclude_regex", help="Exclude repositories matching the regex"
    )


def find_workspace_path() -> Path:
    """
    Find the workspace path when not specified on the command line.
    """
    # Walk up the file system hierarchy until a `.tsrc` directory is found
    head = os.getcwd()
    tail = "a truthy string"
    while tail:
        tsrc_path = os.path.join(head, ".tsrc")
        if os.path.isdir(tsrc_path):
            return Path(head)

        else:
            head, tail = os.path.split(head)
    raise Error("Could not find current workspace")


def get_workspace_with_repos(
    namespace: argparse.Namespace,
    ignore_if_group_not_found: bool = False,
    ignore_group_item: bool = False,
) -> Workspace:
    workspace = get_workspace(namespace, silent=ignore_if_group_not_found)
    workspace.repos = resolve_repos(
        workspace,
        groups=namespace.groups,
        all_cloned=namespace.all_cloned,
        include_regex=namespace.include_regex,
        exclude_regex=namespace.exclude_regex,
        ignore_if_group_not_found=ignore_if_group_not_found,
        ignore_group_item=ignore_group_item,
    )
    return workspace


def simulate_get_workspace_with_repos(
    namespace: argparse.Namespace,
) -> List[str]:
    workspace = get_workspace(namespace, silent=True)
    return simulate_resolve_repos(
        workspace,
        groups=namespace.groups,
        all_cloned=namespace.all_cloned,
        include_regex=namespace.include_regex,
        exclude_regex=namespace.exclude_regex,
        ignore_if_group_not_found=True,
        ignore_group_item=True,
    )


def simulate_resolve_repos(
    workspace: Workspace,
    *,
    singular_remote: str = "",
    groups: Optional[List[str]],
    all_cloned: bool,
    include_regex: str = "",
    exclude_regex: str = "",
    ignore_if_group_not_found: bool = False,
    ignore_group_item: bool = False,
) -> List[str]:
    """
    just to obatin 'groups_seen'
    as if we hit the exception, we may miss some groups
    """
    # Handle --all-cloned and --groups
    if ignore_group_item is True:
        manifest = workspace.get_manifest_safe_mode(ManifestsTypeOfData.LOCAL)
    else:
        manifest = workspace.get_manifest()

    if groups:
        manifest.get_repos(groups=groups, ignore_if_group_not_found=True)
        if manifest.group_list:
            return manifest.group_list.get_groups_seen()
    return []


def resolve_repos(
    workspace: Workspace,
    *,
    singular_remote: str = "",
    groups: Optional[List[str]],
    all_cloned: bool,
    include_regex: str = "",
    exclude_regex: str = "",
    do_switch: bool = False,
    ignore_if_group_not_found: bool = False,
    ignore_group_item: bool = False,
) -> List[Repo]:
    """
    Given a workspace with its config and its local manifest,
    and a collection of parsed command  line arguments,
    return the list of repositories to operate on.
    """
    # Handle --all-cloned and --groups
    if ignore_group_item is True:
        manifest = workspace.get_manifest_safe_mode(ManifestsTypeOfData.LOCAL)
    else:
        manifest = workspace.get_manifest()
    repos = []

    if groups:
        repos = manifest.get_repos(
            groups=groups, ignore_if_group_not_found=ignore_if_group_not_found
        )
    elif do_switch is True:
        repos = manifest.get_repos(groups, do_switch)
    elif all_cloned:
        repos = manifest.get_repos(all_=True)
        repos = [repo for repo in repos if (workspace.root_path / repo.dest).exists()]
    else:
        repos = repos_from_config(
            manifest, workspace.config, silent=ignore_if_group_not_found
        )

    if singular_remote:
        filtered_repos = []
        for repo in repos:
            remotes = [
                remote
                for remote in repo.remotes
                if singular_remote.lower() == remote.name.lower()
            ]
            if remotes:
                filtered_repos.append(repo)
        repos = filtered_repos

    if include_regex:
        repos = [repo for repo in repos if re.search(include_regex, repo.dest)]

    if exclude_regex:
        repos = [repo for repo in repos if not re.search(exclude_regex, repo.dest)]

    # At this point, nothing was requested on the command line, time to
    # use the workspace configuration:
    return repos


def resolve_repos_without_workspace(
    manifest: Manifest,
    gac: GroupsAndConstraints,
) -> List[Repo]:
    """
    Use just Manifest to get Repos in regard of Groups,
    include_regex, exclude_regex. Also respect 'singular_remote'
    If no Groups are provided, consider all Repos there are.
    Return Repos to operate on.
    """
    repos = []

    if gac.groups:
        # due to we are working with Manifest, there is
        # no reason to enforce group to exist
        repos = manifest.get_repos(groups=gac.groups, ignore_if_group_not_found=True)
    else:
        repos = manifest.get_repos(all_=True)

    if gac.singular_remote:
        filtered_repos = []
        for repo in repos:
            remotes = [
                remote
                for remote in repo.remotes
                if gac.singular_remote.lower() == remote.name.lower()
            ]
            if remotes:
                filtered_repos.append(repo)
        repos = filtered_repos

    if gac.include_regex:
        repos = [repo for repo in repos if re.search(gac.include_regex, repo.dest)]

    if gac.exclude_regex:
        repos = [repo for repo in repos if not re.search(gac.exclude_regex, repo.dest)]

    return repos


def is_match_repo_dest_on_inc_excl(
    gac: GroupsAndConstraints,
    i_r_d: str,
) -> bool:
    if (
        (gac.include_regex and re.search(gac.include_regex, i_r_d))  # noqa: W503
        or not gac.include_regex  # noqa: W503
    ) and (
        (gac.exclude_regex and not re.search(gac.exclude_regex, i_r_d))  # noqa: W503
        or not gac.exclude_regex  # noqa: W503
    ):
        return True
    return False


def resolve_repos_apply_constraints(
    repos: List[Repo],
    gac: GroupsAndConstraints,
) -> List[Repo]:
    # NOTE: code duplication, see Fn above, and above above
    """
    Use just constraints on Repos in GroupAndConstraints class
    to filter Repos. Consider:
    include_regex, exclude_regex. Also respect 'singular_remote'
    """
    if gac.singular_remote:
        filtered_repos = []
        for repo in repos:
            remotes = [
                remote
                for remote in repo.remotes
                if gac.singular_remote.lower() == remote.name.lower()
            ]
            if remotes:
                filtered_repos.append(repo)
        repos = filtered_repos

    if gac.include_regex:
        repos = [repo for repo in repos if re.search(gac.include_regex, repo.dest)]

    if gac.exclude_regex:
        repos = [repo for repo in repos if not re.search(gac.exclude_regex, repo.dest)]

    return repos


def repos_from_config(
    manifest: Manifest,
    workspace_config: WorkspaceConfig,
    silent: bool = False,
) -> List[Repo]:
    """
    Given a workspace config, returns a list of repos.

    """
    clone_all_repos = workspace_config.clone_all_repos
    repo_groups = workspace_config.repo_groups

    if clone_all_repos:
        # workspace config contains clone_all_repos: true,
        # return everything
        return manifest.get_repos(all_=True)
    if repo_groups:
        # workspace config contains some groups, use that,
        # fmt: off
        if silent is False:
            ui.info(
                ui.green, "*", ui.reset, "Using groups from workspace config:",
                ", ".join(repo_groups),
            )
        # fmt: on
        return manifest.get_repos(groups=repo_groups, ignore_if_group_not_found=silent)
    else:
        # workspace config does not specify clone_all_repos nor
        # a list of groups, ask the manifest for the list of default
        # repos
        return manifest.get_repos(groups=None)
