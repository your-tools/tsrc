""" Entry point for `tsrc sync` """

from pathlib import Path
from typing import List, Optional

import cli_ui as ui

from tsrc.cli import get_workspace, repos_arg, resolve_repos


@repos_arg
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
