""" Common tools for tsrc commands """

from typing import List
import argparse
import os

import cli_ui as ui
from path import Path

import tsrc
from tsrc.workspace.config import WorkspaceConfig
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
    manifest = workspace.get_manifest()
    config = workspace.config
    workspace.repos = resolve_repos(manifest, args=args, workspace_config=config)
    if args.all_repos:
        workspace.repos = [
            x for x in workspace.repos if (workspace.root_path / x.src).exists()
        ]
    return workspace


def resolve_repos(
    manifest: Manifest, *, args: argparse.Namespace, workspace_config: WorkspaceConfig
) -> List[tsrc.Repo]:
    if args.all_repos:
        return manifest.get_repos(all_=True)

    if args.groups:
        return manifest.get_repos(groups=args.groups)

    # At this point, nothing was requested on the command line, time to
    # use the workspace configuration
    return repos_from_config(manifest, workspace_config)


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
