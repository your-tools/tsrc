""" Main tsrc entry point """

import argparse
import functools
import importlib
import os
import sys
import textwrap
from typing import Callable, List, Optional

import colored_traceback
import ui

import tsrc

ArgsList = Optional[List[str]]
MainFunc = Callable[..., None]


def fix_cmd_args_for_foreach(args: argparse.Namespace,
                             foreach_parser: argparse.ArgumentParser) -> None:
    """ We want to support both:
      $ tsrc foreach -c 'shell command'
     and
      $ tsrc foreach -- some-cmd --some-opts

    Due to argparse limitations, args.cmd will always be
    a list, but we nee a *string* when using 'shell=True'

    So transform the argparse.Namespace object to have
    * args.cmd suitable  to pass to subprocess later
    * args.cmd_as_str suitable for display purposes

    """
    def die(message: str) -> None:
        ui.error(message)
        print(foreach_parser.epilog, end="")
        sys.exit(1)

    if args.shell:
        if len(args.cmd) != 1:
            die("foreach -c must be followed by exactly one argument")
        cmd = args.cmd[0]
        cmd_as_str = cmd
    else:
        cmd = args.cmd
        if not cmd:
            die("needs a command to run")
        cmd_as_str = " ".join(cmd)

    args.cmd = cmd
    args.cmd_as_str = cmd_as_str


def add_workspace_subparser(
        subparser: argparse._SubParsersAction, name: str) -> argparse.ArgumentParser:
    parser = subparser.add_parser(name)
    parser.add_argument("-w", "--workspace", dest="workspace_path")
    return parser


def main_wrapper(main_func: MainFunc) -> MainFunc:
    """ Wraps main() entry point to better deal with errors """
    @functools.wraps(main_func)
    def wrapped(args: ArgsList = None) -> None:
        colored_traceback.add_hook()
        try:
            main_func(args=args)
        except tsrc.Error as e:
            # "expected" failure, display it and exit
            if e.message:
                ui.error(e.message)
            sys.exit(1)
        except KeyboardInterrupt:
            ui.warning("Interrupted by user, quitting")
            sys.exit(1)
    return wrapped


def setup_ui(args: argparse.Namespace) -> None:
    verbose = None
    if os.environ.get("VERBOSE"):
        verbose = True
    if args.verbose:
        verbose = args.verbose
    ui.setup(verbose=verbose, quiet=args.quiet, color=args.color)


@main_wrapper
def main(args: ArgsList = None) -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument("--verbose", help="Show debug messages",
                        action="store_true")
    parser.add_argument("-q", "--quiet", help="Only display warnings and errors",
                        action="store_true")
    parser.add_argument("--color", choices=["auto", "always", "never"])

    subparsers = parser.add_subparsers(title="subcommands", dest="command")

    subparsers.add_parser("version")

    foreach_parser = add_workspace_subparser(subparsers, "foreach")
    foreach_parser.add_argument("cmd", nargs="*")
    foreach_parser.add_argument("-c", dest="shell", action="store_true")
    foreach_parser.add_argument("-g", "--group", action="append", dest="groups")
    foreach_parser.epilog = textwrap.dedent("""\
    Usage:
       # Run command directly
       tsrc foreach -- some-cmd --with-option
    Or:
       # Run command through the shell
       tsrc foreach -c 'some cmd'
    """)
    foreach_parser.formatter_class = argparse.RawDescriptionHelpFormatter

    init_parser = add_workspace_subparser(subparsers, "init")
    init_parser.add_argument("url", nargs="?")
    init_parser.add_argument("-b", "--branch")
    init_parser.add_argument("-g", "--group", action="append", dest="groups")
    init_parser.add_argument("-s", "--shallow", action="store_true", dest="shallow", default=False)
    init_parser.set_defaults(branch="master")

    log_parser = add_workspace_subparser(subparsers, "log")
    log_parser.add_argument("--from", required=True, dest="from_", metavar="FROM")
    log_parser.add_argument("--to")
    log_parser.set_defaults(to="HEAD")

    push_parser = add_workspace_subparser(subparsers, "push")
    push_parser.add_argument("-f", "--force", action="store_true", default=False)
    push_parser.add_argument("-t", "--target", dest="target_branch")
    push_parser.add_argument("push_spec", nargs="?")
    push_parser.add_argument("-a", "--assignee", dest="assignee")
    push_parser.add_argument("-r", "--reviewer", "--approver", dest="reviewers", action="append",
                             help="Request review from the given users")

    github_group = push_parser.add_argument_group("github options")
    github_group.add_argument("--merge", help="Merge pull request", action="store_true")

    gitlab_group = push_parser.add_argument_group("gitlab options")
    gitlab_group.add_argument("--accept", action="store_true")
    gitlab_group.add_argument("--close", action="store_true")

    message_group = gitlab_group.add_mutually_exclusive_group()
    message_group.add_argument("--title", dest="title")
    message_group.add_argument("--wip", action="store_true", help="Mark merge request as WIP")
    message_group.add_argument("--ready", action="store_true", help="Mark merge request as ready")

    add_workspace_subparser(subparsers, "status")
    add_workspace_subparser(subparsers, "sync")

    args_ns = parser.parse_args(args=args)  # type: argparse.Namespace
    setup_ui(args_ns)

    command = args_ns.command
    if not command:
        parser.print_help()
        sys.exit(1)
    module = importlib.import_module("tsrc.cli.%s" % command)
    if command == "foreach":
        fix_cmd_args_for_foreach(args_ns, foreach_parser)

    return module.main(args_ns)  # type: ignore
