""" Entry point for tsrc sync """

import argparse
import cli_ui as ui

import tsrc.cli


def main(args: argparse.Namespace) -> None:
    workspace = tsrc.cli.get_workspace(args)
    ui.info_2("Updating manifest")
    workspace.update_manifest()

    config = workspace.config
    groups = config.repo_groups
    all_repos = config.clone_all_repos
    if groups and not all_repos:
        ui.info(ui.green, "*", ui.reset, "Using groups from config:", ", ".join(groups))
    if all_repos:
        ui.info(ui.green, "*", ui.reset, "Synchronizing all repos")

    workspace.clone_missing()
    workspace.set_remotes()
    workspace.sync(force=args.force)
    workspace.copy_files()
    ui.info("Done", ui.check)
