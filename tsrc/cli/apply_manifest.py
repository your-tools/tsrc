""" Entry point for `tsrc apply-manifest`. """

from pathlib import Path
from typing import Any

import cli_ui as ui
from argh import arg

import tsrc.manifest
from tsrc.cli import repos_from_config, workspace_action, workspace_arg


@workspace_arg  # type: ignore
@workspace_action
@arg("manifest_path", help="path to the local manifest", type=Path)  # type: ignore
def apply_manifest(
    workspace: tsrc.Workspace, manifest_path: Path, **kwargs: Any
) -> None:
    """ apply a local manifest file """
    ui.info_1("Applying manifest from", manifest_path)

    manifest = tsrc.manifest.load(manifest_path)
    workspace.repos = repos_from_config(manifest, workspace.config)
    workspace.clone_missing()
    workspace.set_remotes()
    workspace.perform_filesystem_operations()
