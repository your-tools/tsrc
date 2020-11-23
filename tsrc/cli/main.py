""" Main tsrc entry point. """

import argparse
import functools
import os
import sys
from typing import Callable, Optional, Sequence

import argh
import cli_ui as ui
import colored_traceback

import tsrc

from .apply_manifest import apply_manifest
from .foreach import foreach
from .init import init
from .log import log
from .status import status
from .sync import sync
from .version import version

ArgsList = Optional[Sequence[str]]
MainFunc = Callable[..., None]


def main_wrapper(main_func: MainFunc) -> MainFunc:
    """ Wraps main() entry point to better deal with errors. """

    @functools.wraps(main_func)
    def wrapped(args: ArgsList = None) -> None:
        colored_traceback.add_hook()
        try:
            main_func(args=args)
        except tsrc.Error as e:
            # "expected" failure, display it and exit note: we allow
            # tsrc.Error instances to have an empty message. In that
            # case, do not print anything and assume relevant info has
            # already been printed.
            if e.message:
                ui.error(e.message)
            sys.exit(1)
        except KeyboardInterrupt:
            ui.warning("Interrupted by user, quitting")
            sys.exit(1)

    return wrapped


def setup_ui(args: argparse.Namespace) -> None:
    """Configure the cli_ui package using options
    set on the command line and environment variables.

    """
    verbose = False
    if os.environ.get("VERBOSE"):
        verbose = True
    if args.verbose:
        verbose = args.verbose
    ui.setup(verbose=verbose, quiet=args.quiet, color=args.color)


@main_wrapper
def main(args: ArgsList = None) -> None:
    """ Main entry point. """
    main_impl(args=args)


def testable_main(args: ArgsList) -> None:
    """Same behavior as the main entrypoint, except we never
    hide backtraces when an exception is raised.

    """
    main_impl(args=args)


def main_impl(args: ArgsList = None) -> None:
    parser = argh.ArghParser(prog="tsrc")
    parser.add_argument(
        "--version", action="version", version="tsrc " + tsrc.__version__
    )

    parser.add_argument("--verbose", help="show debug messages", action="store_true")
    parser.add_argument(
        "-q", "--quiet", help="only display warnings and errors", action="store_true"
    )
    parser.add_argument("--color", choices=["auto", "always", "never"])

    parser.add_commands([apply_manifest, init, foreach, version, log, sync, status])

    ui_args = parser.parse_args(args=args)
    setup_ui(ui_args)

    parser.dispatch(argv=args)
