""" Main tsrc entry point """

import argparse
import functools
import importlib
import os
import sys
import textwrap
from typing import Callable, Optional, Sequence

import colored_traceback
import cli_ui as ui
from path import Path

import tsrc

ArgsList = Optional[Sequence[str]]
MainFunc = Callable[..., None]


def fix_cmd_args_for_foreach(
    args: argparse.Namespace, foreach_parser: argparse.ArgumentParser
) -> None:
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
    subparser: argparse._SubParsersAction, name: str
) -> argparse.ArgumentParser:
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
            # note: we allow tsrc.Error instances to have an
            # empty message. In that case, do not print
            # anything and assume relevant info has
            # already been printed
            if e.message:
                ui.error(e.message)
            sys.exit(1)
        except KeyboardInterrupt:
            ui.warning("Interrupted by user, quitting")
            sys.exit(1)

    return wrapped


def setup_ui(args: argparse.Namespace) -> None:
    verbose = False
    if os.environ.get("VERBOSE"):
        verbose = True
    if args.verbose:
        verbose = args.verbose
    ui.setup(verbose=verbose, quiet=args.quiet, color=args.color)


def testable_main(args: ArgsList) -> None:
    main_impl(args=args)


@main_wrapper
def main(args: ArgsList = None) -> None:
    main_impl(args=args)


def main_impl(args: ArgsList = None) -> None:
    parser = argparse.ArgumentParser(prog="tsrc")
    parser.add_argument(
        "--version", action="version", version="tsrc " + tsrc.__version__
    )

    parser.add_argument("--verbose", help="Show debug messages", action="store_true")
    parser.add_argument(
        "-q", "--quiet", help="Only display warnings and errors", action="store_true"
    )
    parser.add_argument("--color", choices=["auto", "always", "never"])

    subparsers = parser.add_subparsers(title="subcommands", dest="command")

    subparsers.add_parser("version")

    foreach_parser = add_workspace_subparser(subparsers, "foreach")
    foreach_parser.add_argument("cmd", nargs="*")
    foreach_parser.add_argument("-c", dest="shell", action="store_true")
    foreach_parser.add_argument("-g", "--group", action="append", dest="groups")
    foreach_parser.add_argument(
        "--groups-from-config",
        action="store_true",
        help="Use groups from the workspace configuration",
        default=False,
    )
    foreach_parser.epilog = textwrap.dedent(
        """\
    Usage:
       # Run command directly
       tsrc foreach -- some-cmd --with-option
    Or:
       # Run command through the shell
       tsrc foreach -c 'some cmd'
    """
    )
    foreach_parser.formatter_class = argparse.RawDescriptionHelpFormatter

    init_parser = add_workspace_subparser(subparsers, "init")
    init_parser.add_argument("url")
    init_parser.add_argument("-b", "--branch")
    init_parser.add_argument("-g", "--group", "--groups", nargs="+", dest="groups")
    init_parser.add_argument(
        "--clone-all-repos",
        action="store_true",
        dest="clone_all_repos",
        help="clone all repos from the manifest, regardless of groups",
    )
    init_parser.add_argument(
        "-s", "--shallow", action="store_true", dest="shallow", default=False
    )
    init_parser.set_defaults(branch="master")

    log_parser = add_workspace_subparser(subparsers, "log")
    log_parser.add_argument("--from", required=True, dest="from_", metavar="FROM")
    log_parser.add_argument("--to")
    log_parser.set_defaults(to="HEAD")

    add_workspace_subparser(subparsers, "status")

    sync_parser = add_workspace_subparser(subparsers, "sync")
    sync_parser.add_argument("--force", action="store_true")

    apply_manifest = add_workspace_subparser(subparsers, "apply-manifest")
    apply_manifest.add_argument("manifest_path", type=Path)

    args_ns = parser.parse_args(args=args)  # type: argparse.Namespace
    setup_ui(args_ns)

    command = args_ns.command
    if not command:
        parser.print_help()
        sys.exit(1)
    module = importlib.import_module("tsrc.cli.%s" % command.replace("-", "_"))
    if command == "foreach":
        fix_cmd_args_for_foreach(args_ns, foreach_parser)

    return module.main(args_ns)  # type: ignore
