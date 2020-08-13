""" Entry point for `tsrc apply-manifest` """

from typing import Optional
from argh import arg
from path import Path

import cli_ui as ui

import tsrc.manifest
from tsrc.cli import (
    with_workspace,
    get_workspace,
    repos_from_config,
)


@with_workspace  # type: ignore
@arg("manifest_path", help="path to the local manifest", type=Path)  # type: ignore
def apply_manifest(manifest_path: Path, workspace_path: Optional[Path] = None) -> None:
    """ apply a local manifest file """
    workspace = get_workspace(workspace_path)

    ui.info_1("Applying manifest from", manifest_path)

    manifest = tsrc.manifest.load(manifest_path)
    workspace.repos = repos_from_config(manifest, workspace.config)
    workspace.clone_missing()
    workspace.set_remotes()
    workspace.perform_filesystem_operations()
