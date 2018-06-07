""" Entry point for tsrc sync """

import argparse
import ui

import tsrc.cli


def main(args: argparse.Namespace) -> None:
    workspace = tsrc.cli.get_workspace(args)
    workspace.update_manifest()
    workspace.load_manifest()
    active_groups = workspace.active_groups
    if active_groups:
        ui.info(ui.green, "*", ui.reset, "Using groups:", ",".join(active_groups))
    workspace.clone_missing()
    workspace.set_remotes()
    workspace.sync()
    workspace.copy_files()
    ui.info("Done", ui.check)
