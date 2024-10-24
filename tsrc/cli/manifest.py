""" Entry point for `tsrc manifest`. """

import argparse
from copy import deepcopy

from tsrc.cli import (
    add_repos_selection_args,
    add_workspace_arg,
    get_workspace_with_repos,
    simulate_get_workspace_with_repos,
)
from tsrc.config_data import ConfigUpdateData, ConfigUpdateType
from tsrc.executor import process_items
from tsrc.groups import GroupNotFound
from tsrc.groups_to_find import GroupsToFind
from tsrc.pcs_repo import (
    get_deep_manifest_from_local_manifest_pcsrepo,
    get_deep_manifest_pcsrepo,
)
from tsrc.status_endpoint import StatusCollector

# from tsrc.status_footer import StatusFooter
from tsrc.status_header import StatusHeader, StatusHeaderDisplayMode
from tsrc.utils import erase_last_line
from tsrc.workspace_repos_summary import WorkspaceReposSummary


def configure_parser(subparser: argparse._SubParsersAction) -> None:
    parser = subparser.add_parser(
        "manifest", description="View and manage top-level Manifest's configuration"
    )
    parser.add_argument(
        "-b",
        "--branch",
        help="change Manifest's branch for future sync",
        dest="manifest_branch",
    )
    add_workspace_arg(parser)
    add_repos_selection_args(parser)
    # same option as in 'status'
    parser.add_argument(
        "--no-mm",
        action="store_false",
        help="do not display Manifest marker",
        dest="use_manifest_marker",
    )
    parser.add_argument(
        "--no-dm",
        action="store_false",
        help="do not display Deep Manifest",
        dest="use_deep_manifest",
    )
    parser.add_argument(
        "--no-fm",
        action="store_false",
        help="do not display Future Manifest",
        dest="use_future_manifest",
    )
    parser.add_argument(
        "--same-fm",
        action="store_true",
        help="use buffered Future Manifest to speed-up execution",
        dest="use_same_future_manifest",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="do not check for leftover's GIT descriptions",
        dest="strict_on_git_desc",
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
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> None:
    gtf = GroupsToFind(args.groups)
    groups_seen = simulate_get_workspace_with_repos(args)
    gtf.found_these(groups_seen)

    try:
        workspace = get_workspace_with_repos(
            args, ignore_group_item=args.ignore_group_item
        )
    except GroupNotFound:
        # try to obtain workspace ignoring group error
        # if group is found in Deep Manifest or Future Manifest,
        # do not report GroupNotFound.
        # if not, than raise exception at the very end
        workspace = get_workspace_with_repos(
            args,
            ignore_if_group_not_found=True,
            ignore_group_item=args.ignore_group_item,
        )

    dm = None
    if args.use_deep_manifest is True:
        dm, gtf = get_deep_manifest_from_local_manifest_pcsrepo(
            workspace,
            gtf,
        )

    wrs = WorkspaceReposSummary(
        workspace,
        gtf,
        dm,
        only_manifest=True,
        manifest_marker=args.use_manifest_marker,
        future_manifest=args.use_future_manifest,
        use_same_future_manifest=args.use_same_future_manifest,
    )

    workspace_config = workspace.config

    status_header = StatusHeader(
        workspace,
        # display both: 'url' and 'branch'
        [StatusHeaderDisplayMode.URL, StatusHeaderDisplayMode.BRANCH],
    )
    if args.manifest_branch:
        cfg_update_data = ConfigUpdateData(manifest_branch=args.manifest_branch)
        status_header.register_change(
            cfg_update_data, [ConfigUpdateType.MANIFEST_BRANCH]
        )
    status_header.display()
    status_collector = StatusCollector(
        workspace, ignore_group_item=args.ignore_group_item
    )

    repos = deepcopy(workspace.repos)

    wrs.prepare_repos()

    if args.strict_on_git_desc is False:
        repos += wrs.obtain_leftovers_repos(repos)

    if repos:
        # get repos to process, in this case it will be just 1
        these_repos, _ = get_deep_manifest_pcsrepo(repos, workspace_config.manifest_url)

        # num_jobs=1 as we will have only (max) 1 repo to process
        process_items(these_repos, status_collector, num_jobs=1)
        erase_last_line()

        statuses = status_collector.statuses

        wrs.ready_data(
            statuses,
        )
        wrs.separate_leftover_statuses(workspace.repos)

        # only calculate summary when there are some Workspace repos
        if workspace.repos:
            wrs.summary()

    # if the normal Repo(s) were not found,
    # there still may be some Deep Manifest or Future manifest leftovers
    wrs.check_for_leftovers()

    # check if we have found all Groups (if any provided)
    # and if not, throw exception ManifestGroupNotFound
    wrs.must_match_all_groups(ignore_if_group_not_found=args.ignore_if_group_not_found)
