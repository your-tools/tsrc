""" Entry point for `tsrc foreach`. """

import argparse
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import List, Union

import cli_ui as ui

import tsrc
from tsrc.cli import (
    add_repos_selection_args,
    add_workspace_arg,
    get_workspace_with_repos,
)

EPILOG = textwrap.dedent(
    """\
    Usage:
       # Run command directly
       tsrc foreach -- some-cmd --with-option
    Or:
       # Run command through the shell
       tsrc foreach -c 'some cmd'
    """
)

Command = Union[str, List[str]]


def configure_parser(subparser: argparse._SubParsersAction) -> None:
    parser = subparser.add_parser(
        "foreach", epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    add_workspace_arg(parser)
    add_repos_selection_args(parser)
    parser.add_argument("cmd", nargs="*")
    parser.add_argument(
        "-c",
        help="use a shell to run the command",
        dest="shell",
        default=False,
        action="store_true",
    )
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> None:
    # Note:
    # we want to support both:
    #  $ tsrc foreach -c 'shell command'
    #  and
    #  $ tsrc foreach -- some-cmd --some-opts
    #
    # Due to argparse limitations, `cmd` will always be a list,
    # but we need a *string* when using 'shell=True'.
    #
    # So transform use the value from `cmd` and `shell` so that:
    # * action.command is suitable as argument to pass to subprocess.run()
    # * action.description is suitable for display purposes
    command: Command = []
    if args.shell:
        if len(args.cmd) != 1:
            die("foreach -c must be followed by exactly one argument")
        command = args.cmd[0]
        description = args.cmd[0]
    else:
        if not args.cmd:
            die("needs a command to run")
        command = args.cmd
        description = " ".join(args.cmd)
    shell = args.shell
    command = command
    description = description

    workspace = get_workspace_with_repos(args)

    cmd_runner = CmdRunner(workspace.root_path, command, description, shell=shell)
    tsrc.run_sequence(workspace.repos, cmd_runner)
    ui.info("OK", ui.check)


class CommandFailed(tsrc.Error):
    pass


class CouldNotStartProcess(tsrc.Error):
    pass


class CmdRunner(tsrc.Task[tsrc.Repo]):
    """
    Implements a Task that runs the same command on several repositories.
    """

    def __init__(
        self,
        workspace_path: Path,
        command: Command,
        description: str,
        shell: bool = False,
    ) -> None:
        self.workspace_path = workspace_path
        self.command = command
        self.description = description
        self.shell = shell

    def display_item(self, repo: tsrc.Repo) -> str:
        return repo.dest

    def on_start(self, *, num_items: int) -> None:
        ui.info_1(f"Running `{self.description}` on {num_items} repos")

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
            ui.reset, ui.bold, self.description,
            sep=""
        )
        # fmt: on
        full_path = self.workspace_path / repo.dest
        try:
            rc = subprocess.call(self.command, cwd=full_path, shell=self.shell)
        except OSError as e:
            raise CouldNotStartProcess("Error when starting process:", e)
        if rc != 0:
            raise CommandFailed()


def die(message: str) -> None:
    ui.error(message)
    print(EPILOG, end="")
    sys.exit(1)


class MissingRepo(tsrc.Error):
    def __init__(self, dest: str):
        self.dest = dest
        super().__init__("not cloned")
