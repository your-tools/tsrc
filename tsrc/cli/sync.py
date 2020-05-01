""" Entry point for tsrc sync """

import argparse
import cli_ui as ui

import tsrc.cli


def main(args: argparse.Namespace) -> None:
    workspace = tsrc.cli.get_workspace(args)

    ui.info_2("Updating manifest")
    workspace.update_manifest()

    workspace.repos = tsrc.cli.resolve_repos(workspace, args=args)
    workspace.clone_missing()
    workspace.set_remotes()
    workspace.sync(force=args.force)
    workspace.perform_filesystem_operations()
    ui.info("Done", ui.check)
