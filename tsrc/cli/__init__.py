""" Common tools for tsrc commands """

import functools
from typing import Any, Callable, List, Optional
import os

from argh import arg
import cli_ui as ui
from path import Path

import tsrc
from tsrc.workspace.config import WorkspaceConfig
from tsrc.workspace import Workspace
from tsrc.manifest import Manifest


def composed(*decorators: Callable) -> Callable:
    """ Build a decorator by composing a list of decorator """

    def inner(f: Callable) -> Callable:
        for decorator in reversed(decorators):
            f = decorator(f)
        return f

    return inner


workspace_arg = arg(
    "-w",
    "--workspace",
    dest="workspace_path",
    help="path to the current workspace",
    type=Path,
)
groups_arg = arg(
    "-g", "--group", "--groups", nargs="+", dest="groups", help="groups to use"
)
all_cloned_arg = arg(
    "--all-cloned",
    action="store_true",
    dest="all_cloned",
    help="run on all cloned repos",
)


def repos_arg(f: Callable) -> Callable:
    return composed(workspace_arg, groups_arg, all_cloned_arg)(f)  # type: ignore


def workspace_action(f: Callable) -> Callable:
    @functools.wraps(f)
    def res(*args: Any, workspace_path: Optional[Path] = None, **kwargs: Any) -> Any:
        if not workspace_path:
            workspace_path = find_workspace_path()
        workspace = tsrc.Workspace(workspace_path)
        return f(workspace, *args, **kwargs)

    return res


def repos_action(f: Callable) -> Callable:
    @functools.wraps(f)
    def res(
        *args: Any,
        workspace_path: Optional[Path] = None,
        groups: Optional[List[str]] = None,
        all_cloned: bool = False,
        **kwargs: Any
    ) -> Any:
        if not workspace_path:
            workspace_path = find_workspace_path()
        workspace = tsrc.Workspace(workspace_path)
        workspace.repos = resolve_repos(workspace, groups, all_cloned)
        return f(workspace, *args, **kwargs)

    return res


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


def get_workspace(workspace_path: Optional[Path]) -> tsrc.Workspace:
    if not workspace_path:
        workspace_path = find_workspace_path()
    return tsrc.Workspace(workspace_path)


def get_workspace_with_repos(
    workspace_path: Path, groups: Optional[List[str]], all_cloned: bool
) -> tsrc.Workspace:
    workspace = get_workspace(workspace_path)
    workspace.repos = resolve_repos(workspace, groups, all_cloned)
    return workspace


def resolve_repos(
    workspace: Workspace, groups: Optional[List[str]], all_cloned: bool
) -> List[tsrc.Repo]:
    """"
    Given a workspace with its config and its local manifest,
    and a collection of parsed command  line arguments,
    return the list of repositories to operate on.
    """
    # Handle --all-cloned and --groups
    manifest = workspace.get_manifest()
    if groups:
        return manifest.get_repos(groups=groups)

    if all_cloned:
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
