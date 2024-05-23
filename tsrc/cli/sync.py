""" Entry point for `tsrc sync` """

import argparse
from typing import List

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
        "--no-update-config",
        action="store_false",
        dest="update_config_repo_groups",
        help="leave configured repo_groups intact when no groups are provided",
    )
    parser.add_argument(
        "--ignore-missing-groups",
        action="store_true",
        dest="ignore_if_group_not_found",
        help="ignore configured group(s) if it is not found in groups defined in manifest",
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
    update_config_repo_groups = args.update_config_repo_groups
    groups = args.groups
    all_cloned = args.all_cloned
    singular_remote = args.singular_remote
    include_regex = args.include_regex
    exclude_regex = args.exclude_regex
    correct_branch = args.correct_branch
    workspace = get_workspace(args)
    num_jobs = get_num_jobs(args)

    ignore_if_group_not_found: bool = False
    report_update_repo_groups: bool = False

    if update_manifest:
        ui.info_2("Updating manifest")
        workspace.update_manifest()

        # check if groups needs to be ignored
        if groups and args.ignore_if_group_not_found is True:
            local_manifest = workspace.local_manifest.get_manifest()
            found_groups: List[str] = []
            if local_manifest.group_list and local_manifest.group_list.groups:
                found_groups = list(
                    set(groups).intersection(local_manifest.group_list.groups)
                )
                # workspace.update_config_repo_groups_provided(found_groups)
                workspace.update_config_repo_groups(groups=found_groups)
                report_update_repo_groups = True

        if update_config_repo_groups is True and args.ignore_if_group_not_found is True:
            ignore_if_group_not_found = True
        if update_config_repo_groups and not groups:
            workspace.update_config_repo_groups(groups=None)
            report_update_repo_groups = True

        if report_update_repo_groups is True:
            ui.info_2("Updating repo_groups")
        else:
            ui.info_2("Leaving repo_groups intact")
    else:
        ui.info_2("Not updating manifest")

    workspace.repos = resolve_repos(
        workspace,
        singular_remote=singular_remote,
        groups=groups,
        all_cloned=all_cloned,
        include_regex=include_regex,
        exclude_regex=exclude_regex,
        ignore_if_group_not_found=ignore_if_group_not_found,
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
