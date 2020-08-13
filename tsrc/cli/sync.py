""" Entry point for tsrc sync """

from typing import List, Optional
import cli_ui as ui
from path import Path

from tsrc.cli import (
    with_workspace,
    with_groups,
    with_all_cloned,
    get_workspace,
    resolve_repos,
)


@with_workspace  # type: ignore
@with_groups  # type: ignore
@with_all_cloned  # type: ignore
def sync(
    workspace_path: Optional[Path] = None,
    groups: Optional[List[str]] = None,
    all_cloned: bool = False,
    force: bool = False,
) -> None:
    """ synchronize the current workspace with the manifest """
    workspace = get_workspace(workspace_path)

    ui.info_2("Updating manifest")
    workspace.update_manifest()

    workspace.repos = resolve_repos(workspace, groups=groups, all_cloned=all_cloned)
    workspace.clone_missing()
    workspace.set_remotes()
    workspace.sync(force=force)
    workspace.perform_filesystem_operations()
    ui.info("Done", ui.check)
