""" Entry point for `tsrc init` """
import argparse
import os

from path import Path
import ui

import tsrc
import tsrc.workspace.manifest_config


def main(args: argparse.Namespace) -> None:
    workspace_path = args.workspace_path or os.getcwd()
    workspace = tsrc.Workspace(Path(workspace_path))
    ui.info_1("Configuring workspace in", ui.bold, workspace_path)
    manifest_config = tsrc.workspace.ManifestConfig.from_args(args)
    workspace.configure_manifest(manifest_config)
    workspace.load_manifest()
    workspace.clone_missing()
    workspace.set_remotes()
    workspace.copy_files()
    ui.info("Done", ui.check)
