""" Common tools for tsrc commands """

from typing import List
import argparse
import os

import cli_ui as ui
from path import Path

import tsrc
from tsrc.workspace.config import WorkspaceConfig
from tsrc.workspace import Workspace
from tsrc.manifest import Manifest


def find_workspace_path() -> Path:
    """ Look for a workspace root somewhere in the upper directories
    hierarchy

    """
    head = os.getcwd()
    tail = "a truthy string"
    while tail:
        tsrc_path = os.path.join(head, ".tsrc")
        if os.path.isdir(tsrc_path):
            return Path(head)

        else:
            head, tail = os.path.split(head)
    raise tsrc.Error("Could not find current workspace")


def get_workspace(args: argparse.Namespace) -> tsrc.Workspace:
    if args.workspace_path:
        workspace_path = Path(args.workspace_path)
    else:
        workspace_path = find_workspace_path()
    return tsrc.Workspace(workspace_path)


def get_workspace_with_repos(args: argparse.Namespace) -> tsrc.Workspace:
    workspace = get_workspace(args)
    workspace.repos = resolve_repos(workspace, args=args)
    return workspace


def resolve_repos(workspace: Workspace, args: argparse.Namespace) -> List[tsrc.Repo]:
    """"
    Given a workspace with its config and its local manifest,
    and a collection of parsed command  line arguments,
    return the list of repositories to operate on.
    """
    # Handle --all-cloned and --groups
    manifest = workspace.get_manifest()
    if args.groups:
        return manifest.get_repos(groups=args.groups)

    if args.all_cloned:
        repos = manifest.get_repos(all_=True)
        return [repo for repo in repos if (workspace.root_path / repo.dest).exists()]

    # At this point, nothing was requested on the command line, time to
    # use the workspace configuration
    return repos_from_config(manifest, workspace.config)


def repos_from_config(
    manifest: Manifest, workspace_config: WorkspaceConfig
) -> List[tsrc.Repo]:
    clone_all_repos = workspace_config.clone_all_repos
    repo_groups = workspace_config.repo_groups

    if clone_all_repos:
        # workspace config contains clone_all_repos: true,
        # return everything
        return manifest.get_repos(all_=True)
    if repo_groups:
        # workspace config contains some groups, use that,
        # fmt: off
        ui.info(
            ui.green, "*", ui.reset, "Using groups from workspace config:",
            ", ".join(repo_groups),
        )
        # fmt: on
        return manifest.get_repos(groups=repo_groups)
    else:
        # workspace config does not specify clone_all_repos nor
        # a list of groups, ask the manifest for the list of default
        # repos
        return manifest.get_repos(groups=None)
