""" Entry point for tsrc status """

import argparse

import cli_ui as ui

from tsrc.cli import (
    add_num_jobs_arg,
    add_repos_selection_args,
    add_workspace_arg,
    get_num_jobs,
    get_workspace_with_repos,
    simulate_get_workspace_with_repos,
)
from tsrc.executor import process_items
from tsrc.groups import GroupNotFound
from tsrc.groups_to_find import GroupsToFind
from tsrc.manifest_common import ManifestGroupNotFound
from tsrc.pcs_repo import get_deep_manifest_pcsrepo, is_manifest_in_workspace
from tsrc.status_endpoint import StatusCollector
from tsrc.status_header import StatusHeader, StatusHeaderDisplayMode

# from tsrc.status_header import header_manifest_branch
from tsrc.utils import erase_last_line
from tsrc.workspace_repos_summary import WorkspaceReposSummary


def configure_parser(subparser: argparse._SubParsersAction) -> None:
    parser = subparser.add_parser("status")
    add_workspace_arg(parser)
    add_repos_selection_args(parser)
    add_num_jobs_arg(parser)
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="more verbose if available",
        dest="more_verbose",
    )
    parser.add_argument(
        "--no-mm",
        action="store_true",
        help="do not display Manifest marker",
        dest="no_manifest_marker",
    )
    parser.add_argument(
        "--no-dm",
        action="store_true",
        help="do not display Deep Manifest",
        dest="no_deep_manifest",
    )
    parser.add_argument(
        "--no-fm",
        action="store_true",
        help="do not display Future Manifest",
        dest="no_future_manifest",
    )
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> None:
    gtf = GroupsToFind(args.groups)
    groups_seen = simulate_get_workspace_with_repos(args)
    gtf.found_these(groups_seen)

    try:
        workspace = get_workspace_with_repos(args)
    except GroupNotFound:
        # TODO: only allow this if there are certain conditions:
        # * apprise desc is enabled (displaying Future Manifest)
        # * Manifest branch is about to change => apprise desc

        # try to obtain workspace ignoring group error
        # if group is found in Deep Manifest or Future Manifest,
        # do not report it.
        # if not, than raise exception at the end
        workspace = get_workspace_with_repos(args, ignore_if_group_not_found=True)

    wrs = WorkspaceReposSummary(
        workspace,
        gtf,
        manifest_marker=not args.no_manifest_marker,
    )

    status_header = StatusHeader(
        workspace,
        [StatusHeaderDisplayMode.BRANCH],
    )
    status_header.display()
    status_collector = StatusCollector(workspace)
    repos = workspace.repos
    if not repos:
        ui.info_2("Workspace is empty")
        # check if perhaps there is change in
        # manifest branch, thus Future Manifest
        # can be obtained, check if the Future Manifest
        # does not match given group(s) (or default group)
        wrs.dry_check_future_manifest()
        return

    ui.info_1(f"Collecting statuses of {len(repos)} repo(s)")
    num_jobs = get_num_jobs(args)
    process_items(repos, status_collector, num_jobs=num_jobs)
    erase_last_line()

    _, dm = get_deep_manifest_pcsrepo(repos, workspace.config.manifest_url)

    sm = None
    if args.no_deep_manifest is False:
        sm = is_manifest_in_workspace(workspace, repos)
    if args.no_deep_manifest is True:
        print("DEBUG ::--no-dm::")
        dm = None

    if sm:
        # TODO: unfortunately this is not enough. there is possibility that
        # Deep Manifest will not be displayed even if it exist.
        # Groups may select only such repos, that does not have any
        # repo that is currently in the workspace.
        ui.info_2("Workspace status, including [Deep Manifest branches]:")
    else:
        ui.info_2("Workspace status:")

    statuses = status_collector.statuses

    # TODO: apprise should be set by input parameter
    #    wrs = WorkspaceReposSummary(
    #        workspace,
    #        statuses,
    #        dm,
    #        args.groups,
    #        apprise=True,
    #    )
    wrs.ready_data(
        statuses,
        dm,
        apprise=not args.no_future_manifest,
        # apprise=False,
    )
    wrs.summary()
    try:
        wrs.must_match_all_groups()  # and if not, throw exception
    except ManifestGroupNotFound as e:
        ui.error(e)
        return
