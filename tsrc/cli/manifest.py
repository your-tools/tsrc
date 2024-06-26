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
from tsrc.workspace_repos_summary import WorkspaceReposSummary


def configure_parser(subparser: argparse._SubParsersAction) -> None:
    parser = subparser.add_parser("manifest")
    add_workspace_arg(parser)
    add_repos_selection_args(parser)
    parser.add_argument(
        "--branch",
        help="use this branch for the manifest",
        dest="manifest_branch",
    )
    # same option as in 'status'
    parser.add_argument(
        "--no-mm",
        action="store_false",
        help="do not display Manifest marker",
        dest="no_manifest_marker",
    )
    parser.add_argument(
        "--no-dm",
        action="store_false",
        help="do not display Deep Manifest",
        dest="no_deep_manifest",
    )
    parser.add_argument(
        "--no-fm",
        action="store_false",
        help="do not display Future Manifest",
        dest="no_future_manifest",
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
        # if group is found in Future Manifest, do not report it
        # if not, than raise exception again
        workspace = get_workspace_with_repos(args, ignore_if_group_not_found=True)

    dm = None
    if args.no_deep_manifest is True:
        dm, gtf = get_deep_manifest_from_local_manifest_pcsrepo(
            workspace,
            gtf,
        )

    wrs = WorkspaceReposSummary(
        workspace,
        gtf,
        dm,
        only_manifest=True,
        manifest_marker=args.no_manifest_marker,
        future_manifest=args.no_future_manifest,
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
    status_collector = StatusCollector(workspace)

    repos = deepcopy(workspace.repos)

    wrs.prepare_repos()

    if args.strict_on_git_desc is False:
        repos += wrs.obtain_leftovers_repos(repos)

    if repos:
        # get repos to process, in this case it will be just 1
        these_repos, _ = get_deep_manifest_pcsrepo(repos, workspace_config.manifest_url)

        # num_jobs=1 as we will have only (max) 1 repo to process
        process_items(these_repos, status_collector, num_jobs=1)

        statuses = status_collector.statuses

        wrs.ready_data(
            statuses,
        )
        wrs.separate_leftover_statuses(workspace.repos)

        # only calculate summary when there are some Workspace repos
        if workspace.repos:
            wrs.summary()

    # check if perhaps there is change in
    # manifest branch, thus Future Manifest
    # can be obtained, check if the Future Manifest
    # does not match given group(s) (or default group)
    wrs.check_for_leftovers()

    # if some group is not found, 'ManifestGroupNotFound' will be thrown
    wrs.must_match_all_groups()
