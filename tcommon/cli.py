""" Common tools for tbuild's scripts """

import functools
import sys

import colored_traceback

from tcommon import ui
import tcommon


def main_wrapper(main_func):
    @functools.wraps(main_func)
    def wrapped(args=None):
        colored_traceback.add_hook()
        try:
            main_func(args=args)
        except tcommon.Error as e:
            # "expected" failure, display it and exit
            ui.error(e)
            sys.exit(1)
        except SystemExit as e:
            # `tcommon.fatal()` or `sys.exit()` has been called,
            # assume message has already been displayed and
            # exit accordingly
            sys.exit(e.code)
        except KeyboardInterrupt:
            ui.warning("Interrupted by user, quitting")
            sys.exit(1)
        except Exception as e:
            # This is a bug: raise so that `cgitb` displays
            # an helpful backtrace
            raise
    return wrapped
