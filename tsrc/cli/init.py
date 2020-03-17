""" Entry point for `tsrc init` """
import argparse
import os

from path import Path
import cli_ui as ui

import tsrc
from tsrc.workspace import Workspace
from tsrc.workspace.config import WorkspaceConfig


def main(args: argparse.Namespace) -> None:
    path_as_str = args.workspace_path or os.getcwd()
    workspace_path = Path(path_as_str)
    cfg_path = workspace_path / ".tsrc" / "config.yml"

    if cfg_path.exists():
        raise tsrc.Error("Workspace already configured with file " + cfg_path)

    ui.info_1("Configuring workspace in", ui.bold, workspace_path)

    workspace_config = WorkspaceConfig(
        manifest_url=args.url,
        manifest_branch=args.branch,
        clone_all_repos=args.clone_all_repos,
        repo_groups=args.groups,
        shallow_clones=args.shallow,
    )

    workspace_config.save_to_file(cfg_path)

    workspace = Workspace(workspace_path)
    workspace.update_manifest()
    workspace.clone_missing()
    workspace.set_remotes()
    workspace.copy_files()
    ui.info_2("Workspace initialized")
    ui.info_2("Configuration written in", ui.bold, workspace.cfg_path)
