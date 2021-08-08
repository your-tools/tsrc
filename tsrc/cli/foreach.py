""" Entry point for `tsrc foreach`. """

import argparse
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import cli_ui as ui

from tsrc.cli import (
    add_num_jobs_arg,
    add_repos_selection_args,
    add_workspace_arg,
    get_num_jobs,
    get_workspace_with_repos,
)
from tsrc.cli.env_setter import EnvSetter
from tsrc.errors import Error, MissingRepo
from tsrc.executor import Outcome, Task, process_items
from tsrc.repo import Repo
from tsrc.workspace import Workspace

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
    add_num_jobs_arg(parser)
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
    num_jobs = get_num_jobs(args)

    workspace = get_workspace_with_repos(args)
    cmd_runner = CmdRunner(workspace.root_path, command, description, shell=shell)
    repos = workspace.repos
    ui.info_1(f"Running `{description}` on {len(repos)} repos")
    collection = process_items(repos, cmd_runner, num_jobs=num_jobs)
    errors = collection.errors
    if errors:
        ui.error(f"Command failed for {len(errors)} repo(s)")
        if cmd_runner.parallel:
            # Print output of failed commands that were hidden
            for (item, error) in errors.items():
                ui.info(item)
                ui.info("-" * len(item))
                ui.info(error)
        else:
            # Just print the repos
            for item in errors:
                ui.info(ui.green, "*", ui.reset, item)
        raise ForeachError()
    else:
        ui.info("OK", ui.check)


class DetailedCommandError(Error):
    def __init__(
        self,
        *,
        working_path: Path,
        cmd: str,
        rc: int,
        output: Optional[str] = None,
    ) -> None:
        self.cmd = cmd
        self.working_path = working_path
        self.output = output
        self.rc = rc
        message = f"`{cmd}` from {working_path} exited with code {rc}"
        if output:
            message += "\n" + output
        super().__init__(message)


class CommandError(Error):
    pass


class CouldNotStartProcess(Error):
    pass


class ForeachError(Error):
    pass


class CmdRunner(Task[Repo]):
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
        workspace = Workspace(workspace_path)
        self.env_setter = EnvSetter(workspace)

    def describe_item(self, item: Repo) -> str:
        return item.dest

    def describe_process_start(self, item: Repo) -> List[ui.Token]:
        return [item.dest]

    def describe_process_end(self, item: Repo) -> List[ui.Token]:
        return [ui.green, "ok", ui.reset, item.dest]

    def process(self, index: int, count: int, repo: Repo) -> Outcome:
        # Note:
        #  When self.parallel is True, this task will be run in parallel with
        #  other tasks.
        #
        #  So we need to:
        #    * capture the output of the commands we are running
        #    * raise a DetailedCommandError instance if a command's return code
        #      is 0 (because otherwise the output of the command is lost)
        #
        # When self.parallel is False, we don't capture the output, which means we
        # can't raise a DetailedCommandError. Instead, we raise a plain CommandError
        # instance. This means the user has to go up in the output to see the output
        # of the command that failed, but also that the command output are printed
        # in real time.
        full_path = self.workspace_path / repo.dest
        if not full_path.exists():
            raise MissingRepo(repo.dest)
        # fmt: off
        self.info(
            ui.brown,
            self.workspace_path / repo.dest,
            " ",
            ui.lightgray, "$ ",
            ui.reset, self.description,
            sep=""
        )
        # fmt: on
        full_path = self.workspace_path / repo.dest
        run_env = self.env_setter.get_env_for_repo(repo)
        run_env.update(os.environ)
        try:
            kwargs: Dict[str, Any] = {
                "cwd": full_path,
                "shell": self.shell,
                "env": run_env,
            }
            if self.parallel:
                kwargs["stdout"] = subprocess.PIPE
                kwargs["stderr"] = subprocess.STDOUT
            process = subprocess.run(self.command, **kwargs, universal_newlines=True)
        except OSError as e:
            raise CouldNotStartProcess("Error when starting process:", e)
        if process.returncode != 0:
            if self.parallel:
                raise DetailedCommandError(
                    working_path=full_path,
                    cmd=self.description,
                    rc=process.returncode,
                    output=process.stdout,
                )
            else:
                raise CommandError()
        return Outcome.empty()


def die(message: str) -> None:
    ui.error(message)
    print(EPILOG, end="")
    sys.exit(1)
