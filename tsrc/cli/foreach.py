""" Entry point for tsrc foreach """

import subprocess

import ui

import tsrc.cli
import tsrc.workspace


class CommandFailed(tsrc.Error):
    pass


class CmdRunner(tsrc.executor.Task):
    def __init__(self, workspace, cmd, cmd_as_str, shell=False):
        self.workspace = workspace
        self.cmd = cmd
        self.cmd_as_str = cmd_as_str
        self.shell = shell

    def display_item(self, repo):
        return repo.src

    def description(self):
        return "Running `%s` on every repo" % self.cmd_as_str

    def process(self, repo):
        ui.info(repo.src, "\n",
                ui.lightgray, "$ ",
                ui.reset, ui.bold, self.cmd_as_str,
                sep="")
        full_path = self.workspace.joinpath(repo.src)
        rc = subprocess.call(self.cmd, cwd=full_path, shell=self.shell)
        if rc != 0:
            raise CommandFailed()


def main(args):
    workspace = tsrc.cli.get_workspace(args)
    workspace.load_manifest()
    cmd_runner = CmdRunner(workspace, args.cmd, args.cmd_as_str, shell=args.shell)
    tsrc.executor.run_sequence(workspace.get_repos(), cmd_runner)
    ui.info("OK", ui.check)
