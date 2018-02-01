""" tsrc foreach """

import subprocess

import click
import ui

import tsrc.cli
import tsrc.workspace
from tsrc.cli import workspace_cli


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


@click.command("foreach")
@click.option("-c", "--shell", is_flag=True)
@click.argument("cmd", metavar="<cmd>", nargs=-1, required=True)
@workspace_cli
def main(ctx, *, cmd, shell):
    """ Run the same command on several repositories

    Use -- to separate options for your command and tsrc options:

        $ tsrc --verbose foreach -- ls --all

    And use -c to start a shell:

        $ tsrc foreach -c 'cd src && ls'

    """
    workspace = ctx.obj["workspace"]
    workspace.load_manifest()
    cmd_as_str = " ".join(cmd)
    cmd_runner = CmdRunner(workspace, cmd, cmd_as_str, shell=shell)
    tsrc.executor.run_sequence(workspace.get_repos(), cmd_runner)
    ui.info("OK", ui.check)
