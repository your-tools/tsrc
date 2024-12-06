""" Entry point for tsrc status """

import argparse
from copy import deepcopy
from typing import Dict, List, Union, cast

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
from tsrc.local_tmp_bare_repos import (
    prepare_tmp_bare_dm_repos,
    process_bare_repos,
    ready_tmp_bare_repos,
)
from tsrc.manifest_common_data import ManifestsTypeOfData
from tsrc.pcs_repo import get_deep_manifest_from_local_manifest_pcsrepo
from tsrc.repo import Repo
from tsrc.status_endpoint import (
    BareStatus,
    Status,
    StatusCollector,
    StatusCollectorLocalOnly,
)
from tsrc.status_header import StatusHeader, StatusHeaderDisplayMode
from tsrc.utils import erase_last_line

# from tsrc.status_header import header_manifest_branch
from tsrc.workspace_repos_summary import WorkspaceReposSummary


def configure_parser(subparser: argparse._SubParsersAction) -> None:
    parser = subparser.add_parser(
        "status",
        description="Report Status of repositories of current Workspace. Also report Deep Manifest, Future Manifest and Manifest Marker if presnet.",  # noqa: E501
    )
    add_workspace_arg(parser)
    add_repos_selection_args(parser)
    add_num_jobs_arg(parser)
    parser.add_argument(
        "--show-leftovers-status",
        action="store_true",
        help="show full GIT status also for leftovers, if there are some, that have valid repository on the filesystem. here hard error about the repository is ignored and no status is displayed",  # noqa: E501
        dest="show_leftovers_status",
    )
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
        "--local-git-only",
        action="store_true",
        help="do not process anything that will lead to remote connection",
        dest="local_git_only",
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
            args,
            ignore_if_group_not_found=args.ignore_if_group_not_found,
            ignore_group_item=args.ignore_group_item,
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

    # DM (if present) + bare DM (if DM and present)
    dm = None
    bare_dm_repos: List[Repo] = []
    if args.use_deep_manifest is True:
        dm, gtf = get_deep_manifest_from_local_manifest_pcsrepo(
            workspace,
            gtf,
        )
        if dm and args.local_git_only is False:
            # this require to check remote
            bare_dm_repos = prepare_tmp_bare_dm_repos(
                workspace, dm, gtf, num_jobs=get_num_jobs(args)
            )

    wrs = WorkspaceReposSummary(
        workspace,
        gtf,
        dm,
        manifest_marker=args.use_manifest_marker,
        future_manifest=args.use_future_manifest,
        use_same_future_manifest=args.use_same_future_manifest,
        show_leftovers_status=args.show_leftovers_status,
    )

    status_header = StatusHeader(
        workspace,
        [StatusHeaderDisplayMode.BRANCH],
    )
    status_header.display()
    status_collector: Union[StatusCollector, StatusCollectorLocalOnly]
    if args.local_git_only is True:
        status_collector = StatusCollectorLocalOnly(
            workspace, ignore_group_item=args.ignore_group_item
        )
    else:
        status_collector = StatusCollector(
            workspace, ignore_group_item=args.ignore_group_item
        )

    repos = deepcopy(workspace.repos)
    bare_fm_repos = wrs.get_bare_fm_repos()
    bare_fm_repos = ready_tmp_bare_repos(
        workspace, ManifestsTypeOfData.FUTURE, bare_fm_repos
    )
    bare_repos = bare_fm_repos + bare_dm_repos
    bare_repos = process_bare_repos(workspace, bare_repos, num_jobs=get_num_jobs(args))
    repos += bare_repos

    wrs.prepare_repos()

    leftovers_repos: List[Repo] = []
    if args.strict_on_git_desc is False:
        leftovers_repos = wrs.obtain_leftovers_repos(repos)
        repos += leftovers_repos

    if repos:

        # status_header.report_collecting(len(repos))
        status_header.report_collecting(
            len(workspace.repos), len(leftovers_repos), len(bare_repos)
        )

        num_jobs = get_num_jobs(args)
        process_items(repos, status_collector, num_jobs=num_jobs)
        erase_last_line()

        statuses = status_collector.statuses

        wrs.ready_data(
            # TODO: this crazines is there due to 'StatusCollectorLocalOnly' is possible
            cast(Dict[str, Union[Status, Exception, BareStatus, Exception]], statuses),
        )
        wrs.separate_statuses(bare_repos)
        wrs.calculate_fields_len()

        # only calculate summary when there are some Workspace repos
        if workspace.repos:
            wrs.summary()

    # if the normal Repo(s) were not found,
    # there still may be some Deep Manifest or Future manifest leftovers
    wrs.check_for_leftovers()

    # check if we have found all Groups (if any provided)
    # and if not, throw exception ManifestGroupNotFound
    wrs.must_match_all_groups(ignore_if_group_not_found=args.ignore_if_group_not_found)
