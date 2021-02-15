""" Entry point for `tsrc sync` """

import argparse

import cli_ui as ui

from tsrc.cli import (
    add_repos_selection_args,
    add_workspace_arg,
    get_workspace,
    resolve_repos,
)


def configure_parser(subparser: argparse._SubParsersAction) -> None:
    parser = subparser.add_parser("sync")
    add_workspace_arg(parser)
    add_repos_selection_args(parser)
    parser.set_defaults(update_manifest=True, force=False)
    parser.add_argument(
        "--force", help="use `git fetch --force` while syncing", action="store_true"
    )
    parser.add_argument(
        "--no-update-manifest",
        action="store_false",
        dest="update_manifest",
        help="skip updating the manifest before synching repositories",
    )
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> None:
    force = args.force
    update_manifest = args.update_manifest
    groups = args.groups
    all_cloned = args.all_cloned

    workspace = get_workspace(args)

    if update_manifest:
        ui.info_2("Updating manifest")
        workspace.update_manifest()
    else:
        ui.info_2("Not updating manifest")

    workspace.repos = resolve_repos(workspace, groups=groups, all_cloned=all_cloned)

    workspace.clone_missing()
    workspace.set_remotes()
    workspace.sync(force=force)
    workspace.perform_filesystem_operations()
    ui.info("Done", ui.check)
