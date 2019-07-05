""" Entry point for `tsrc init` """
import argparse
import os

import attr
from path import Path
import cli_ui as ui

import tsrc
from tsrc.workspace.manifest_config import ManifestConfig


def main(args: argparse.Namespace) -> None:
    workspace_path = args.workspace_path or os.getcwd()
    workspace = tsrc.Workspace(Path(workspace_path))
    ui.info_1("Configuring workspace in", ui.bold, workspace_path)
    as_dict = vars(args)
    relevant_keys = [x.name for x in attr.fields(ManifestConfig)]
    for key in list(as_dict.keys()):
        if key not in relevant_keys:
            del as_dict[key]
    manifest_config = ManifestConfig.from_dict(as_dict)
    workspace.configure_manifest(manifest_config)
    workspace.load_manifest()
    workspace.clone_missing()
    workspace.set_remotes()
    workspace.copy_files()
    ui.info("Done", ui.check)
