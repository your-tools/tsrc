""" Entry point for `tsrc sync` """

import argparse

import cli_ui as ui

from tsrc.cli import (
    add_num_jobs_arg,
    add_repos_selection_args,
    add_workspace_arg,
    get_num_jobs,
    get_workspace,
    resolve_repos,
)


def configure_parser(subparser: argparse._SubParsersAction) -> None:
    parser = subparser.add_parser("sync")
    add_workspace_arg(parser)
    add_repos_selection_args(parser)
    parser.set_defaults(update_manifest=True, force=False, correct_branch=True)
    parser.add_argument(
        "--force", help="use `git fetch --force` while syncing", action="store_true"
    )
    parser.add_argument(
        "--no-update-manifest",
        action="store_false",
        dest="update_manifest",
        help="skip updating the manifest before syncing repositories",
    )
    parser.add_argument(
        "--no-correct-branch",
        action="store_false",
        dest="correct_branch",
        help="prevent going back to the configured branch, if the repo is clean",
    )
    parser.add_argument(
        "-r",
        "--singular-remote",
        help="only use this remote when cloning repositories",
    )
    add_num_jobs_arg(parser)
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> None:
    force = args.force
    update_manifest = args.update_manifest
    groups = args.groups
    all_cloned = args.all_cloned
    singular_remote = args.singular_remote
    include_regex = args.include_regex
    exclude_regex = args.exclude_regex
    correct_branch = args.correct_branch
    workspace = get_workspace(args)
    num_jobs = get_num_jobs(args)

    if update_manifest:
        ui.info_2("Updating manifest")
        workspace.update_manifest()
    else:
        ui.info_2("Not updating manifest")

    workspace.repos = resolve_repos(
        workspace,
        singular_remote=singular_remote,
        groups=groups,
        all_cloned=all_cloned,
        include_regex=include_regex,
        exclude_regex=exclude_regex,
    )

    workspace.clone_missing(num_jobs=num_jobs)
    workspace.set_remotes(num_jobs=num_jobs)
    workspace.sync(
        force=force,
        singular_remote=singular_remote,
        correct_branch=correct_branch,
        num_jobs=num_jobs,
    )
    workspace.perform_filesystem_operations()
    ui.info_1("Workspace synchronized")
