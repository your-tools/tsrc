""" Entry point for `tsrc manifest`. """

import argparse

import cli_ui as ui

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
from tsrc.manifest_common import ManifestGroupNotFound
from tsrc.pcs_repo import get_deep_manifest_pcsrepo
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
        "--same-fm",
        action="store_true",
        help="use buffered Future Manifest to speed-up execution",
        dest="use_same_future_manifest",
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

    wrs = WorkspaceReposSummary(
        workspace,
        gtf,
        only_manifest=True,
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
    all_repos = workspace.repos
    if not all_repos:
        # check if perhaps there is change in
        # manifest branch, thus Future Manifest
        # can be obtained, check if the Future Manifest
        # does not match given group(s) (or default group)
        wrs.dry_check_future_manifest()
        return

    # get repos to process, in this case it will be just 1
    repos, dm = get_deep_manifest_pcsrepo(all_repos, workspace_config.manifest_url)

    # num_jobs=1 as we will have only (max) 1 repo to process
    process_items(repos, status_collector, num_jobs=1)

    statuses = status_collector.statuses

    wrs.ready_data(
        statuses,
        dm,
        apprise=True,
    )

    wrs.summary()

    try:
        wrs.must_match_all_groups()
    except ManifestGroupNotFound as e:
        ui.error(e)
        return


#    dm_repo = None
#    if dm:
#        dm_repo = repo_from_pcsrepo(dm)
#
#    mi = ManifestReport(
#        workspace,
#        workspace_config,
#        cfg_path,
#        workspace.root_path,
#        statuses,
#        args.manifest_branch,
#        sm,
#        dm_repo,
#    )
#
#    # print main Manifest status
#    mi.report()


#
#    # hand-over data
#    footer = StatusFooter(mi.ready_footer())
#
#    # in addidtion, print footer (what will happen after 'sync')
#    footer.report()


# StatusOrError = Union[Status, Exception]
