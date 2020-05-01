""" Entry point for tsrc foreach """

from typing import List
import argparse
import subprocess

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
        return repo.dest

    def on_start(self, *, num_items: int) -> None:
        ui.info_1(f"Running `{self.cmd_as_str}` on {num_items} repos")

    def on_failure(self, *, num_errors: int) -> None:
        ui.error(f"Command failed for {num_errors} repo(s)")

    def process(self, index: int, count: int, repo: tsrc.Repo) -> None:
        ui.info_count(index, count, repo.dest)
        full_path = self.workspace_path / repo.dest
        if not full_path.exists():
            raise MissingRepo(repo.dest)
        # fmt: off
        ui.info(
            ui.lightgray, "$ ",
            ui.reset, ui.bold, self.cmd_as_str,
            sep=""
        )
        # fmt: on
        full_path = self.workspace_path / repo.dest
        try:
            rc = subprocess.call(self.cmd, cwd=full_path, shell=self.shell)
        except OSError as e:
            raise CouldNotStartProcess("Error when starting process:", e)
        if rc != 0:
            raise CommandFailed()


def main(args: argparse.Namespace) -> None:
    workspace = tsrc.cli.get_workspace_with_repos(args)
    cmd_runner = CmdRunner(
        workspace.root_path, args.cmd, args.cmd_as_str, shell=args.shell
    )
    tsrc.run_sequence(workspace.repos, cmd_runner)
    ui.info("OK", ui.check)


class MissingRepo(tsrc.Error):
    def __init__(self, dest: str):
        self.dest = dest
        super().__init__("not cloned")
