""" Main tsrc entry point """

import argparse
import functools
import importlib
import sys
import textwrap

import colored_traceback

import tsrc
from tsrc import ui


def fix_cmd_args_for_foreach(args, foreach_parser):
    """ We want to support both:

        tsrc foreach -c 'shell command'

     and
        tsrc foreach -- some-cmd --some-opts

    Due to argparse limitations, args.cmd will always be
    a list, but we nee a *string* when using 'shell=True'

    So transform the argparse.Namespace object to have
    * args.cmd suitable  to pass to subprocess later
    * args.cmd_as_str suitable for display purposes

    """
    def die(message):
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


def workspace_subparser(subparser, name):
    parser = subparser.add_parser(name)
    parser.add_argument("-w", "--workspace", dest="workspace_path")
    return parser


def main_wrapper(main_func):
    """ Wraps main() entry point to better deal with errors """
    @functools.wraps(main_func)
    def wrapped(args=None):
        colored_traceback.add_hook()
        try:
            main_func(args=args)
        except tsrc.Error as e:
            # "expected" failure, display it and exit
            ui.error(e)
            sys.exit(1)
        except SystemExit as e:
            # `ui.fatal()` or `sys.exit()` has been called,
            # assume message has already been displayed and
            # exit accordingly
            sys.exit(e.code)
        except KeyboardInterrupt:
            ui.warning("Interrupted by user, quitting")
            sys.exit(1)
        except Exception as e:
            # This is a bug: raise so that colored_traceback prints
            # an helpful backtrace
            raise
    return wrapped


@main_wrapper
def main(args=None):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title="subcommands",
                                       dest="command")

    subparsers.add_parser("version")

    foreach_parser = workspace_subparser(subparsers, "foreach")
    foreach_parser.add_argument("cmd", nargs="*")
    foreach_parser.add_argument("-c", dest="shell", action="store_true")
    foreach_parser.epilog = textwrap.dedent("""\
    Usage:
       # Run command directly
       tsrc foreach -- some-cmd --with-option
    Or:
       # Run command through the shell
       tsrc foreach -c 'some cmd'
    """)
    foreach_parser.formatter_class = argparse.RawDescriptionHelpFormatter

    init_parser = workspace_subparser(subparsers, "init")
    init_parser.add_argument("manifest_url")
    init_parser.add_argument("-b", "--branch")
    init_parser.set_defaults(branch="master")

    log_parser = workspace_subparser(subparsers, "log")
    log_parser.add_argument("--from", required=True, dest="from_", metavar="FROM")
    log_parser.add_argument("--to")
    log_parser.set_defaults(to="HEAD")

    push_parser = workspace_subparser(subparsers, "push")
    push_parser.add_argument("--accept", action="store_true", default=False)
    push_parser.add_argument("-f", "--force", action="store_true", default=False)
    push_parser.add_argument("-t", "--target", dest="target_branch", default="master")
    message_group = push_parser.add_mutually_exclusive_group()
    message_group.add_argument("-m", "--message", dest="mr_title")
    message_group.add_argument("--wip", action="store_true", help="Mark merge request as WIP")
    message_group.add_argument("--ready", action="store_true", help="Mark merge request as ready")
    push_parser.add_argument("-a", "--assignee", dest="assignee")
    workspace_subparser(subparsers, "status")
    workspace_subparser(subparsers, "sync")

    args = parser.parse_args(args=args)
    command = args.command
    if not command:
        parser.print_help()
        sys.exit(1)
    module = importlib.import_module("tsrc.cli.%s" % command)
    if command == "foreach":
        fix_cmd_args_for_foreach(args, foreach_parser)

    return module.main(args)
