""" Entry point for tsrc foreach """

from typing import List, Optional, Tuple
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


def filter_repos(cloned_repos: List[tsrc.Repo],
                 manifest: tsrc.Manifest, *,
                 groups: Optional[List[str]]=None) -> Tuple[List[tsrc.Repo], List[tsrc.Repo]]:

    found = list()  # type: List[tsrc.Repo]
    not_cloned = list()  # type: List[tsrc.Repo]
    from_manifest = manifest.get_repos(groups=groups)
    for repo in from_manifest:
        if repo in cloned_repos:
            found.append(repo)
        else:
            not_cloned.append(repo)
    return (found, not_cloned)


def main(args: argparse.Namespace) -> None:
    workspace = tsrc.cli.get_workspace(args)
    workspace.load_manifest()
    cmd_runner = CmdRunner(workspace, args.cmd, args.cmd_as_str, shell=args.shell)
    manifest = workspace.local_manifest.manifest
    assert manifest
    found, not_cloned = filter_repos(workspace.get_repos(), manifest, groups=args.groups)
    tsrc.run_sequence(found, cmd_runner)
    if not_cloned:
        ui.warning("The following repos were skipped:")
        for repo in not_cloned:
            ui.info("*", repo.src, fileobj=sys.stderr)
    else:
        ui.info("OK", ui.check)
