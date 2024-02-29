""" Entry point for `tsrc manifest`. """

import argparse
from typing import Dict, List, Union

import cli_ui as ui

from pathlib import Path
from tsrc.cli import (
    add_repos_selection_args,
    add_workspace_arg,
    get_workspace_with_repos,
)
from tsrc.executor import process_items
from tsrc.git import run_git_captured
from tsrc.repo import Repo
from tsrc.status_endpoint import Status, StatusCollector, describe_status
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
    # manifest_branch = workspace.local_manifest.current_branch()
    workspace_config = workspace.config

    ui.info_1("Manifest's URL: ", ui.purple, workspace_config.manifest_url, ui.reset)

    status_collector = StatusCollector(workspace)
    repos = workspace.repos
    process_items(repos, status_collector, num_jobs=1)

    statuses = status_collector.statuses

    """'static' as it cannot be changed (till the 'sync');
    "manifest_manifest" = Manifest repo in Manifest.yml;
    this may not exist but if it does, it will be the 'dest'intion == 'direcory_name'"""
    static_manifest_manifest_dest, static_manifest_manifest_branch = \
        is_manifest_in_workspace(repos, workspace.config.manifest_url)

    """current: Workspace's > Manifest_repo's > branch"""
    current_workspace_manifest_repo_branch = None

    if static_manifest_manifest_dest:
        ui.info_2("Integrated into Workspace as another repository:")

    statuses_items = statuses.items()
    current_workspace_manifest_repo_branch = workspace_integration_summary(
        statuses_items,
        static_manifest_manifest_dest,
        static_manifest_manifest_branch,
        workspace.config.manifest_branch
    )

    mi = ManifestInfo(
        workspace_config,
        cfg_path,
        workspace.root_path,
        statuses_items,
        args.manifest_branch,
        static_manifest_manifest_dest,
        static_manifest_manifest_branch,
        current_workspace_manifest_repo_branch
    )

    mi.info()


class ManifestInfo:

    def __init__(
        self,
        workspace_config: WorkspaceConfig,
        cfg_path: Path,
        workspace_root_path: Path,
        statuses_items: Dict[str, Union[Status, Exception]],
        set_manifest_branch: str,
        static_manifest_manifest_dest: str,
        static_manifest_manifest_branch: str,
        current_workspace_manifest_repo_branch: str
    ):
        self.workspace_config = workspace_config
        self.cfg_path = cfg_path
        self.workspace_root_path = workspace_root_path
        self.statuses_items = statuses_items
        self.set_manifest_branch = set_manifest_branch
        self.static_manifest_manifest_dest = static_manifest_manifest_dest
        self.static_manifest_manifest_branch = static_manifest_manifest_branch
        self.current_workspace_manifest_repo_branch = current_workspace_manifest_repo_branch

    def info(self) -> None:
        if self.set_manifest_branch:
            self.on_set_branch()
        else:
            self.on_default_display()

    def on_set_branch(self) -> None:
        """first we need to check if such branch exists in order this to work on 'sync'"""
        rc_is_on_remote = -1
        found_local_branch = False
        if self.static_manifest_manifest_dest:
            rc_is_on_remote, found_local_branch = manifest_branch_exist(
                self.workspace_config.manifest_url,
                self.workspace_root_path / self.static_manifest_manifest_dest,
                self.static_manifest_manifest_dest,
                self.set_manifest_branch
            )
        else:
            rc_is_on_remote = manifest_remote_branch_exist(
                self.workspace_config.manifest_url, self.set_manifest_branch
            )
        if rc_is_on_remote == 0 or found_local_branch:
            """we are good to set new branch"""
            self.uip_using_new_branch(self.set_manifest_branch)
            if self.workspace_config.manifest_branch == self.set_manifest_branch:
                self.uip_skip_set_branch()
            else:
                self.workspace_config.manifest_branch = self.set_manifest_branch
                self.workspace_config.save_to_file(self.cfg_path)
                """workspace is now updated"""
                self.uip_workspace_updated()
                workspace_integration_summary(
                    self.statuses_items,
                    self.static_manifest_manifest_dest,
                    self.static_manifest_manifest_branch,
                    self.workspace_config.manifest_branch,
                    True
                )
                if self.static_manifest_manifest_dest:
                    """when there is Manifest repository in the Workspace"""
                    if rc_is_on_remote == 0:
                        if self.current_workspace_manifest_repo_branch != \
                                self.workspace_config.manifest_branch:
                            self.uip_after_sync_branch_change()
                        else:
                            self.uip_ok_after_sync_same_branch()
                    else:
                        self.uip_push_first_for_sync_to_work()
                else:
                    """use 'manifest_branch_0' to determine if brach will change"""
                    if self.workspace_config.manifest_branch != \
                            self.workspace_config.manifest_branch_0:
                        self.uip_branch_will_change_after_sync(
                            self.workspace_config.manifest_branch,
                            self.workspace_config.manifest_branch_0
                        )
                    else:
                        self.uip_branch_will_stay_the_same_after_sync(
                            self.workspace_config.manifest_branch
                        )
        else:
            """branch is nowhere to be found"""
            if self.static_manifest_manifest_dest:
                """when there is Manifest repository in the Workspace"""
                self.uie_cannot_set_branch_create_first(self.set_manifest_branch)
            else:
                """Workspace without Manifest repository"""
                self.uie_cannot_set_branch_git_push_first(self.set_manifest_branch)

    def on_default_display(self) -> None:
        """just report final status of current state, do not update anything"""
        if self.static_manifest_manifest_dest and \
                self.current_workspace_manifest_repo_branch != \
                self.workspace_config.manifest_branch:
            self.uip_branch_will_change_after_sync(self.workspace_config.manifest_branch)
        else:
            """use 'manifest_branch_0' to determine if brach will change"""
            if self.workspace_config.manifest_branch != self.workspace_config.manifest_branch_0:
                self.uip_branch_will_change_after_sync(
                    self.workspace_config.manifest_branch,
                    self.workspace_config.manifest_branch_0
                )
            else:
                self.uip_branch_will_stay_the_same_after_sync(
                    self.workspace_config.manifest_branch
                )

    def uip_skip_set_branch(self):
        ui.info_1("Skipping configuring the same branch")

    def uip_using_new_branch(self, branch: str):
        ui.info_2("Using new branch: ", ui.green, branch, ui.reset)

    def uip_workspace_updated(self):
        ui.info_1("Workspace updated")

    def uip_after_sync_branch_change(self):
        ui.info_2(
            "After 'sync' the branch will",
            ui.red,
            "(differ)",
            ui.reset,
        )

    def uip_ok_after_sync_same_branch(self):
        ui.info_2(
            ui.blue,
            "OK: After 'sync' the repository will stays on the same branch",
        )

    def uip_push_first_for_sync_to_work(self):
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

    def uie_cannot_set_branch_create_first(self, branch: str):
        ui.error(
            f"Cannot set branch '{branch}' as a new branch as it does not exist. "
            "You need to create it first."
        )

    def uie_cannot_set_branch_git_push_first(self, branch: str):
        ui.error(
            f"Cannot set branch '{branch}' as a new branch as it does not exist. "
            "You need to 'git push' it first."
        )

    def uip_branch_will_change_after_sync(self, branch: str, branch_0: str = ""):
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

    def uip_branch_will_stay_the_same_after_sync(self, branch: str):
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


def is_manifest_in_workspace(repos: List[Repo], workspace_config_manifest_url: str):
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


def workspace_integration_summary(
    statuses_items: Dict[str, StatusOrError],
    st_m_m_dest: str,
    st_m_m_branch: str,
    w_c_m_branch: str,
    do_update: bool = False
):
    """prints a summary of Manifest repository status.
    the same output should be used when using 'tsrc status'
    but other repositories included"""
    cur_w_m_r_branch = None
    for dest, status in statuses_items:
        if dest == st_m_m_dest:
            if do_update:
                ui.info_2(
                    "Updating configured Manifest branch. See new overall state:"
                )
            cur_w_m_r_branch = status.git.branch
            message = [ui.green, "*", ui.reset, dest]
            message += describe_status(status)
            message += [ui.purple, "<---", "MANIFEST:"]
            message += [ui.green, st_m_m_branch]
            if w_c_m_branch != st_m_m_branch:
                message += [
                    ui.reset,
                    "~~~>",
                    ui.green,
                    w_c_m_branch,
                ]
            ui.info(*message)
    return cur_w_m_r_branch


def manifest_remote_branch_exist(url: str, branch: str):
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
        check=False
    )
    return rc


def manifest_branch_exist(
    manifest_url: str,
    full_path: Path,
    static_manifest_manifest_dest: str,
    provided_branch: str
):
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
