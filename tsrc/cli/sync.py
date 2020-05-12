""" Entry point for tsrc sync """

import argparse
import cli_ui as ui

import tsrc.cli


def main(args: argparse.Namespace) -> None:
    workspace = tsrc.cli.get_workspace(args)

    ui.info_2("Updating manifest")
    workspace.update_manifest()

    manifest = workspace.get_manifest()
    workspace.repos = tsrc.cli.resolve_repos(
        manifest, args=args, workspace_config=workspace.config
    )
    workspace.clone_missing()
    workspace.set_remotes()
    workspace.sync(force=args.force)
    workspace.copy_files()
    ui.info("Done", ui.check)
