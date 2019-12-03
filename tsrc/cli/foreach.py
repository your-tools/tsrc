""" Entry point for tsrc foreach """

from typing import List
import argparse
import subprocess
import sys

from path import Path
import cli_ui as ui

import tsrc
import tsrc.cli


class CommandFailed(tsrc.Error):
    pass


class CouldNotStartProcess(tsrc.Error):
    pass


class CmdRunner(tsrc.Task[tsrc.Repo]):
    def __init__(
        self, workspace_path: Path, cmd: List[str], cmd_as_str: str, shell: bool = False
    ) -> None:
        self.workspace_path = workspace_path
        self.cmd = cmd
        self.cmd_as_str = cmd_as_str
        self.shell = shell

    def display_item(self, repo: tsrc.Repo) -> str:
        return repo.src

    def on_start(self, *, num_items: int) -> None:
        ui.info_1("Running `%s` on %d repos" % (self.cmd_as_str, num_items))

    def on_failure(self, *, num_errors: int) -> None:
        ui.error("Command failed for %s repo(s)" % num_errors)

    def process(self, index: int, count: int, repo: tsrc.Repo) -> None:
        ui.info_count(index, count, repo.src)
        # fmt: off
        ui.info(
            ui.lightgray, "$ ",
            ui.reset, ui.bold, self.cmd_as_str,
            sep=""
        )
        # fmt: on
        full_path = self.workspace_path / repo.src
        try:
            rc = subprocess.call(self.cmd, cwd=full_path, shell=self.shell)
        except OSError as e:
            raise CouldNotStartProcess("Error when starting process:", e)
        if rc != 0:
            raise CommandFailed()


def main(args: argparse.Namespace) -> None:
    workspace = tsrc.cli.get_workspace(args)
    cmd_runner = CmdRunner(
        workspace.root_path, args.cmd, args.cmd_as_str, shell=args.shell
    )
    manifest = workspace.local_manifest.get_manifest()
    workspace_config = workspace.config
    groups_from_config = workspace_config.repo_groups

    all_remote_repos = manifest.get_repos(all_=True)
    cloned_repos = [
        x for x in all_remote_repos if (workspace.root_path / x.src).exists()
    ]

    if args.groups_from_config:
        requested_repos = manifest.get_repos(groups=groups_from_config)
    elif args.groups:
        requested_repos = manifest.get_repos(groups=args.groups)
    else:
        requested_repos = cloned_repos

    found = [x for x in requested_repos if x in cloned_repos]
    missing = [x for x in requested_repos if x not in cloned_repos]

    tsrc.run_sequence(found, cmd_runner)
    if missing:
        ui.warning("The following repos were requested but missing from the workspace:")
        for repo in missing:
            ui.info("*", repo.src, fileobj=sys.stderr)
        raise MissingRepos(missing)
    else:
        ui.info("OK", ui.check)


class MissingRepos(tsrc.Error):
    def __init__(self, repos: List[tsrc.Repo]):
        self.repos = repos
