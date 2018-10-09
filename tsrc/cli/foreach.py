""" Entry point for tsrc foreach """

from typing import List
import argparse
import subprocess
import sys

from path import Path
import ui

import tsrc
import tsrc.cli


class CommandFailed(tsrc.Error):
    pass


class CmdRunner(tsrc.Task[tsrc.Repo]):
    def __init__(self, workspace_path: Path, cmd: List[str],
                 cmd_as_str: str, shell: bool = False) -> None:
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

    def process(self, repo: tsrc.Repo) -> None:
        ui.info(repo.src, "\n",
                ui.lightgray, "$ ",
                ui.reset, ui.bold, self.cmd_as_str,
                sep="")
        full_path = self.workspace_path / repo.src
        rc = subprocess.call(self.cmd, cwd=full_path, shell=self.shell)
        if rc != 0:
            raise CommandFailed()


def main(args: argparse.Namespace) -> None:
    workspace = tsrc.cli.get_workspace(args)
    workspace.load_manifest()
    cmd_runner = CmdRunner(workspace.root_path, args.cmd, args.cmd_as_str, shell=args.shell)
    manifest = workspace.local_manifest.manifest
    assert manifest
    cloned_repos = workspace.get_repos()
    requested_repos = manifest.get_repos(groups=args.groups)

    found = [x for x in requested_repos if x in cloned_repos]
    missing = [x for x in requested_repos if x not in cloned_repos]

    tsrc.run_sequence(found, cmd_runner)
    if missing:
        ui.warning("The following repos were skipped:")
        for repo in missing:
            ui.info("*", repo.src, fileobj=sys.stderr)
    else:
        ui.info("OK", ui.check)
