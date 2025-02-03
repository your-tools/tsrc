""" Entry point for `tsrc sync` """

import argparse
from typing import List, Union

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
    parser = subparser.add_parser(
        "sync",
        description="Synchronize Workspace by current configuration of Manifest (see manifest_url and manifest_branch in config)",  # noqa: E501
    )
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
        help="ignore configured group(s) if it is not found in groups defined in manifest. This may be particulary useful when switching Manifest version back when some Groups defined later, was not there yet. In which case we can avoid unecessary Error caused by missing group",  # noqa: E501
    )
    parser.add_argument(
        "--ignore-missing-group-items",
        action="store_true",
        dest="ignore_group_item",
        help="ignore group element if it is not found among Manifest's Repos. WARNING: If you end up in need of this option, you have to understand that you end up with useles Manifest. Warnings will be printed for each Group element that is missing, so it may be easier to fix that. Using this option is NOT RECOMMENDED for normal use",  # noqa: E501
    )
    parser.add_argument(
        "--switch",
        action="store_true",
        dest="do_switch",
        help="change config in accordance to Manifest's switch section. this is pariculary usefull when we wish to change Manifest branch to some version that may have different Groups configured.",  # noqa: E501
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        dest="do_clean",
        help="WARNING: you may loose files that are not under the version control. like such files that are ignored by '.gitignore'. sync to clean state, so the next sync can run smoothly. use with care.",  # noqa: E501
    )
    parser.add_argument(
        "--hard-clean",
        action="store_true",
        dest="do_hard_clean",
        help="WARNING: you may loose files that are not under the version control and also files ignored by '.gitignore'. sync to clean state, that does not even contain ignored files. use with care.",  # noqa: E501
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
    do_switch = args.do_switch
    do_clean = args.do_clean
    do_hard_clean = args.do_hard_clean

    ignore_if_group_not_found: bool = False
    report_update_repo_groups: Union[bool, None] = False

    if update_manifest:
        repo_groups_0 = workspace.config.repo_groups.copy()
        ui.info_2("Updating manifest")
        workspace.update_manifest()

        # check if groups needs to be updated on config
        found_groups: List[str] = []
        if groups:
            local_manifest = workspace.local_manifest.get_manifest()
            if local_manifest.group_list and local_manifest.group_list.groups:
                found_groups = list(
                    set(groups).intersection(local_manifest.group_list.groups)
                )

        if do_switch is True:

            report_update_repo_groups = workspace.update_config_on_switch(
                workspace.local_manifest.get_manifest(), found_groups, groups
            )
            if not isinstance(report_update_repo_groups, bool):
                ui.error("Provided Groups does not match any in the Manifest")
                return
        elif update_config_repo_groups is True:
            workspace.update_config_repo_groups(
                groups=found_groups,
                ignore_group_item=args.ignore_group_item,
                want_groups=groups,
            )
            report_update_repo_groups = True

        if (
            report_update_repo_groups is True
            and repo_groups_0 != workspace.config.repo_groups  # noqa: W503
        ):
            ui.info_2("Updating Workspace Groups configuration")
        else:
            ui.info_2("Leaving Workspace Groups configuration intact")
    else:
        ui.info_2("Not updating manifest")
    if args.ignore_if_group_not_found is True:
        ignore_if_group_not_found = True

    workspace.repos = resolve_repos(
        workspace,
        singular_remote=singular_remote,
        groups=groups,
        all_cloned=all_cloned,
        include_regex=include_regex,
        exclude_regex=exclude_regex,
        do_switch=do_switch,
        ignore_if_group_not_found=ignore_if_group_not_found,
        ignore_group_item=args.ignore_group_item,
    )
    if len(workspace.repos) == 0:
        ui.info_1("Nothing to synchronize, skipping")
        return
    workspace.clone_missing(num_jobs=num_jobs)
    workspace.set_remotes(num_jobs=num_jobs)
    workspace.sync(
        force=force,
        singular_remote=singular_remote,
        correct_branch=correct_branch,
        num_jobs=num_jobs,
    )
    workspace.clean(do_clean=do_clean, do_hard_clean=do_hard_clean, num_jobs=num_jobs)
    workspace.perform_filesystem_operations(ignore_group_item=args.ignore_group_item)
    ui.info_1("Workspace synchronized")
