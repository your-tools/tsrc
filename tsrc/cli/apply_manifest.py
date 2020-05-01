""" Entry point for `tsrc apply-manifest` """

import argparse

import cli_ui as ui
import tsrc.cli


def main(args: argparse.Namespace) -> None:
    workspace = tsrc.cli.get_workspace(args)
    manifest_path = args.manifest_path

    ui.info_1("Applying manifest from", args.manifest_path)
    manifest = tsrc.manifest.load(manifest_path)
    workspace.repos = tsrc.cli.repos_from_config(manifest, workspace.config)
    workspace.clone_missing()
    workspace.set_remotes()
    workspace.perform_filesystem_operations()
