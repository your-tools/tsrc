""" Entry point for tsrc foreach """

import argparse
from typing import List, TypeVar
import subprocess

from path import Path
import ui

import tsrc
import tsrc.cli
import tsrc.workspace


class CommandFailed(tsrc.Error):
    pass


T = TypeVar('T')


class CmdRunner(tsrc.executor.Task[tsrc.Repo]):
    def __init__(self, workspace: Path, cmd: List[str],
                 cmd_as_str: str, shell: bool = False) -> None:
        self.workspace = workspace
        self.cmd = cmd
        self.cmd_as_str = cmd_as_str
        self.shell = shell

    def display_item(self, repo: tsrc.Repo) -> str:
        return repo.src

    def description(self) -> str:
        return "Running `%s` on every repo" % self.cmd_as_str

    def process(self, repo: tsrc.Repo) -> None:
        ui.info(repo.src, "\n",
                ui.lightgray, "$ ",
                ui.reset, ui.bold, self.cmd_as_str,
                sep="")
        full_path = self.workspace.joinpath(repo.src)
        rc = subprocess.call(self.cmd, cwd=full_path, shell=self.shell)
        if rc != 0:
            raise CommandFailed()


def main(args: argparse.Namespace) -> None:
    workspace = tsrc.cli.get_workspace(args)
    workspace.load_manifest()
    cmd_runner = CmdRunner(workspace, args.cmd, args.cmd_as_str, shell=args.shell)
    tsrc.executor.run_sequence(workspace.get_repos(), cmd_runner)
    ui.info("OK", ui.check)
