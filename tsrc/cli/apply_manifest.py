""" Entry point for `tsrc apply-manifest` """

import argparse

import cli_ui as ui
import tsrc.cli
from tsrc.workspace.local_manifest import LocalManifest


def main(args: argparse.Namespace) -> None:
    workspace = tsrc.cli.get_workspace(args)
    manifest_path = args.manifest_path
    ui.info_1("Applying manifest from", args.manifest_path)

    workspace.local_manifest = LocalManifest(manifest_path.parent)
    workspace.clone_missing()
    workspace.set_remotes()
    workspace.copy_files()
