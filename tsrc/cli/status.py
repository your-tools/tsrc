""" Entry point for tsrc status """

import argparse
from copy import deepcopy

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
from tsrc.pcs_repo import get_deep_manifest_from_local_manifest_pcsrepo
from tsrc.status_endpoint import StatusCollector
from tsrc.status_header import StatusHeader, StatusHeaderDisplayMode

# from tsrc.status_header import header_manifest_branch
from tsrc.utils import erase_last_line
from tsrc.workspace_repos_summary import WorkspaceReposSummary


def configure_parser(subparser: argparse._SubParsersAction) -> None:
    parser = subparser.add_parser(
        "status", description="Report Status of repositories of current Workspace."
    )
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
        action="store_false",
        help="do not display Manifest marker",
        dest="use_manifest_marker",
    )
    # TODO: 'no_deep_manifest' now uses wrong logic
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
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> None:
    gtf = GroupsToFind(args.groups)
    groups_seen = simulate_get_workspace_with_repos(args)
    gtf.found_these(groups_seen)

    try:
        workspace = get_workspace_with_repos(args)
    except GroupNotFound:
        # try to obtain workspace ignoring group error
        # if group is found in Deep Manifest or Future Manifest,
        # do not report GroupNotFound.
        # if not, than raise exception at the very end
        workspace = get_workspace_with_repos(args, ignore_if_group_not_found=True)

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
        manifest_marker=args.use_manifest_marker,
        future_manifest=args.use_future_manifest,
        use_same_future_manifest=args.use_same_future_manifest,
    )

    status_header = StatusHeader(
        workspace,
        [StatusHeaderDisplayMode.BRANCH],
    )
    status_header.display()
    status_collector = StatusCollector(workspace)

    repos = deepcopy(workspace.repos)

    wrs.prepare_repos()

    if args.strict_on_git_desc is False:
        repos += wrs.obtain_leftovers_repos(repos)

    if repos:

        status_header.report_collecting(len(repos))

        num_jobs = get_num_jobs(args)
        process_items(repos, status_collector, num_jobs=num_jobs)
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
    wrs.must_match_all_groups()
