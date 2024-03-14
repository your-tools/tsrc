""" Entry point for `tsrc manifest`. """

import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Union

import cli_ui as ui

from tsrc.cli import (
    add_repos_selection_args,
    add_workspace_arg,
    get_workspace_with_repos,
)
from tsrc.executor import process_items
from tsrc.git import get_git_status, run_git_captured
from tsrc.manifest import load_manifest
from tsrc.repo import Repo
from tsrc.status_endpoint import (
    Status,
    StatusCollector,
    WorkspaceReposSummary,
    get_l_and_r_sha1_of_branch,
)
from tsrc.workspace_config import WorkspaceConfig


def configure_parser(subparser: argparse._SubParsersAction) -> None:
    parser = subparser.add_parser("manifest")
    add_workspace_arg(parser)
    add_repos_selection_args(parser)
    parser.add_argument(
        "--branch",
        help="use this branch for the manifest",
        dest="manifest_branch",
    )
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> None:
    workspace = get_workspace_with_repos(args)

    cfg_path = workspace.cfg_path
    workspace_config = workspace.config

    ui.info_1("Manifest's URL:", ui.purple, workspace_config.manifest_url, ui.reset)

    status_collector = StatusCollector(workspace)
    repos = workspace.repos
    process_items(repos, status_collector, num_jobs=1)

    statuses = status_collector.statuses

    """'static' as it cannot be changed (till the 'sync');
    "manifest_manifest" = Manifest repo in Manifest.yml;
    this may not exist but if it does, it will be the 'dest'intion == 'direcory_name'"""
    (
        static_manifest_manifest_dest,
        static_manifest_manifest_branch,
    ) = is_manifest_in_workspace(repos, workspace.config.manifest_url)

    """current: Workspace's > Manifest_repo's > branch"""
    current_workspace_manifest_repo = None

    if static_manifest_manifest_dest:
        ui.info_2("Current integration into Workspace:")

    wrs = WorkspaceReposSummary(
        workspace.root_path,
        statuses,
        static_manifest_manifest_dest,
        static_manifest_manifest_branch,
        workspace.config.manifest_branch,
        only_manifest=True,
    )

    current_workspace_manifest_repo = wrs.summary()

    mi = ManifestReport(
        workspace_config,
        cfg_path,
        workspace.root_path,
        statuses,
        args.manifest_branch,
        static_manifest_manifest_dest,
        static_manifest_manifest_branch,
        current_workspace_manifest_repo,
    )

    mi.report()


class ManifestReport:
    def __init__(
        self,
        workspace_config: WorkspaceConfig,
        cfg_path: Path,
        workspace_root_path: Path,
        statuses: Dict[str, Union[Status, Exception]],
        set_manifest_branch: str,
        static_manifest_manifest_dest: Union[str, None],
        static_manifest_manifest_branch: Union[str, None],
        current_workspace_manifest_repo: Union[Repo, None],
    ):
        self.w_c = workspace_config
        self.cfg_path = cfg_path
        self.workspace_root_path = workspace_root_path
        self.statuses = statuses
        self.set_manifest_branch = set_manifest_branch
        self.s_m_m_dest = static_manifest_manifest_dest
        self.static_manifest_manifest_branch = static_manifest_manifest_branch
        self.c_w_m_repo = current_workspace_manifest_repo

    def report(self) -> None:
        if self.set_manifest_branch:
            self.on_set_branch()
        else:
            self.on_default_display()

    def on_set_branch(self) -> None:
        """first we need to check if such branch exists in order this to work on 'sync'"""
        rc_is_on_remote = -1
        found_local_branch = False
        if self.s_m_m_dest:
            rc_is_on_remote, found_local_branch = manifest_branch_exist(
                self.w_c.manifest_url,
                self.workspace_root_path / self.s_m_m_dest,
                self.s_m_m_dest,
                self.set_manifest_branch,
            )
        else:
            rc_is_on_remote = manifest_remote_branch_exist(
                self.w_c.manifest_url, self.set_manifest_branch
            )
        if rc_is_on_remote == 0 or found_local_branch:
            """we are good to set new branch"""
            self.uip_using_new_branch(self.set_manifest_branch)
            if self.w_c.manifest_branch == self.set_manifest_branch:
                self.uip_skip_set_branch()
            else:
                self.w_c.manifest_branch = self.set_manifest_branch
                self.w_c.save_to_file(self.cfg_path)
                """workspace is now updated"""
                self.uip_workspace_updated()

                wrs = WorkspaceReposSummary(
                    self.workspace_root_path,
                    self.statuses,
                    self.s_m_m_dest,
                    self.static_manifest_manifest_branch,
                    self.w_c.manifest_branch,
                    do_update=True,
                    only_manifest=True,
                )

                wrs.summary()
                self.report_what_after_sync()
        else:
            """branch is nowhere to be found"""
            if self.s_m_m_dest:
                """when there is Manifest repository in the Workspace"""
                self.uie_cannot_set_branch_create_first(self.set_manifest_branch)
            else:
                """Workspace without Manifest repository"""
                self.uie_cannot_set_branch_git_push_first(self.set_manifest_branch)

    def on_default_display(self) -> None:
        """just report final status of current state, do not update anything"""
        self.report_what_after_sync()

    def report_what_after_sync(self) -> None:
        """report what will_happen_after sync with Manifest"""
        if self.s_m_m_dest:
            self.report_iro_m_branch_in_w()
        else:
            """use 'manifest_branch_0' to determine if brach will change"""
            if self.w_c.manifest_branch != self.w_c.manifest_branch_0:
                self.uip_branch_will_change_after_sync(
                    self.w_c.manifest_branch,
                    self.w_c.manifest_branch_0,
                )
            else:
                self.uip_branch_will_stay_the_same_after_sync(self.w_c.manifest_branch)

    def report_iro_m_branch_in_w(self) -> None:
        """report in regards of Manifest branch in Workspace (has change or not)"""
        c_w_m_repo_branch = None
        if self.c_w_m_repo:
            c_w_m_repo_branch = self.c_w_m_repo.branch
        if c_w_m_repo_branch != self.w_c.manifest_branch:
            self.uip_branch_will_change_after_sync(self.w_c.manifest_branch)
        else:
            deep_m_repo = self.get_w_d_m_repo()
            if deep_m_repo:
                if deep_m_repo.branch != self.w_c.manifest_branch:
                    self.uip_branch_will_change_after_sync(self.w_c.manifest_branch)
                else:
                    # manifest repo should have only one remote, thus: [0]
                    if deep_m_repo.remotes[0].url != self.w_c.manifest_url:
                        self.uip_same_branch_different_url(deep_m_repo.remotes[0].url)
                    else:
                        self.uip_ok_after_sync_same_branch()

    def get_w_d_m_repo(self) -> Union[Repo, None]:
        """get Workspace-deep manifest branch. This means:
        Workspace:Manifest repository:Manifest file:Manifest repository:branch"""
        if isinstance(self.s_m_m_dest, str):
            deep_manifest = load_manifest(
                self.workspace_root_path / self.s_m_m_dest / "manifest.yml"
            )
            return deep_manifest.get_repo(self.s_m_m_dest)
        else:
            return None

    """ui prints|errors segment follows:"""

    def uip_skip_set_branch(self) -> None:
        ui.info_1("Skipping configuring the same branch")

    def uip_using_new_branch(self, branch: str) -> None:
        ui.info_2("Using new branch:", ui.green, branch, ui.reset)

    def uip_workspace_updated(self) -> None:
        ui.info_1("Workspace updated")

    def uip_after_sync_branch_change(self) -> None:
        ui.info_2(
            "After 'sync' the branch will",
            ui.red,
            "(differ)",
            ui.reset,
        )

    def uip_same_branch_different_url(self, url: str) -> None:
        ui.info_2("Deep manifest is using different remote URL")
        ui.info_1("Deep Manifest's URL:", url)

    def uip_ok_after_sync_same_branch(self) -> None:
        """check if repository is clean,
        and also if remote commit SHA1 is same as local commit SHA1,
        as only then we can say for sure, it will stays the same"""
        if self.s_m_m_dest:
            m_g_status = get_git_status(self.workspace_root_path / self.s_m_m_dest)
            if not (
                m_g_status.dirty is False  # noqa: W503
                and m_g_status.ahead == 0  # noqa: W503
                and m_g_status.behind == 0  # noqa: W503
                and m_g_status.upstreamed is True  # noqa: W503
            ):
                ui.info_2("Clean Manifest repository before calling 'sync'")
                return
            l_m_sha, r_m_sha = get_l_and_r_sha1_of_branch(
                self.workspace_root_path,
                self.s_m_m_dest,
                self.w_c.manifest_branch,
            )
            if r_m_sha and l_m_sha != r_m_sha:
                ui.info_2("Remote branch does not have same HEAD")
                return
        ui.info_2(
            ui.blue,
            "OK: After 'sync', Manifest repository will stays on the same branch",
        )

    def uip_push_first_for_sync_to_work(self) -> None:
        ui.info_2(
            "You need to",
            ui.red,
            "'git push'",
            ui.reset,
            "this branch to remote in order",
            ui.blue,
            "'sync'",
            ui.reset,
            "to work",
        )

    def uie_cannot_set_branch_create_first(self, branch: str) -> None:
        ui.error(
            f"Cannot set branch '{branch}' as a new branch as it does not exist. "
            "You need to create it first."
        )

    def uie_cannot_set_branch_git_push_first(self, branch: str) -> None:
        ui.error(
            f"Cannot set branch '{branch}' as a new branch as it does not exist. "
            "You need to 'git push' it first."
        )

    def uip_branch_will_change_after_sync(
        self, branch: str, branch_0: str = ""
    ) -> None:
        message = [
            "Currently configured branch on next 'sync' will",
            ui.red,
            "(change):",
        ]
        if branch_0 != "":
            message += [ui.reset, "from:", ui.green, branch_0]
        message += [
            ui.reset,
            "to:",
            ui.green,
            branch,
            ui.reset,
        ]
        ui.info_2(*message)

    def uip_branch_will_stay_the_same_after_sync(self, branch: str) -> None:
        ui.info_2(
            "Currently configured branch on next 'sync' will",
            ui.blue,
            "(stays the same)",
            ui.reset,
            "on:",
            ui.green,
            branch,
            ui.reset,
        )


StatusOrError = Union[Status, Exception]


def is_manifest_in_workspace(
    repos: List[Repo], workspace_config_manifest_url: str
) -> Tuple[Union[str, None], Union[str, None]]:
    static_manifest_manifest_dest = None
    static_manifest_manifest_branch = None
    for x in repos:
        this_dest = x.dest
        this_branch = x.branch
        for y in x.remotes:
            if y.url == workspace_config_manifest_url:
                static_manifest_manifest_dest = this_dest
                static_manifest_manifest_branch = this_branch
    return static_manifest_manifest_dest, static_manifest_manifest_branch


def manifest_remote_branch_exist(url: str, branch: str) -> int:
    """check for manifest remote branch, as only if it exist,
    we should allow to set it. as you can see, there is
    no real path to repository out there"""
    p = Path(".")
    rc, _ = run_git_captured(
        p,
        "ls-remote",
        "--exit-code",
        "--heads",
        url,
        f"refs/heads/{branch}",
        check=False,
    )
    return rc


def manifest_branch_exist(
    manifest_url: str,
    full_path: Path,
    static_manifest_manifest_dest: str,
    provided_branch: str,
) -> Tuple[int, bool]:
    """if there is Manifest repository in the workspace, we can
    check for both remote and local branch if it is exist.
    as only if it is exist, we should allow to set it.

    return 'rc_is_on_remote: Int' and 'found_local_branch: Bool'"""
    found_local_branch = False
    rc_is_on_remote = manifest_remote_branch_exist(manifest_url, provided_branch)

    if rc_is_on_remote != 0:
        """we have not found remote branch. is there at least local one?"""
        if static_manifest_manifest_dest:
            _, full_list_of_branches = run_git_captured(
                full_path,
                "branch",
                '--format="%(refname:short)"',
                check=False,
            )
            for line in full_list_of_branches.splitlines():
                if line.startswith('"' + provided_branch + '"'):
                    found_local_branch = True
                    break
    return rc_is_on_remote, found_local_branch
