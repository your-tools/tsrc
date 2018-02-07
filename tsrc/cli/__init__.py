""" Common tools for tsrc commands """

import click
import functools
import os
import path
import sys

import colored_traceback
import ui

import tsrc
import tsrc.workspace


def main_wrapper(main_func):
    """ Wraps main() entry point to better deal with errors """
    @functools.wraps(main_func)
    def wrapped(*args, **kwargs):
        colored_traceback.add_hook()
        try:
            main_func(*args, **kwargs)
        except tsrc.Error as e:
            # "expected" failure, display it and exit
            if e.message:
                ui.error(e.message)
            sys.exit(1)
        except KeyboardInterrupt:
            ui.warning("Interrupted by user, quitting")
            sys.exit(1)
    return wrapped


def find_workspace_path():
    """ Look for a workspace root somewhere in the upper directories
    hierarchy

    """
    head = os.getcwd()
    tail = True
    while tail:
        tsrc_path = os.path.join(head, ".tsrc")
        if os.path.isdir(tsrc_path):
            return path.Path(head)

        else:
            head, tail = os.path.split(head)
    raise tsrc.Error("Could not find current workspace")


def workspace_cli(func):
    @click.option("-w", "--workspace", metavar="<workspace>")
    @click.pass_context
    @main_wrapper
    @functools.wraps(func)
    def wrapped(ctx, *args, **kwargs):
        ctx.obj = dict()
        ctx.obj["workspace"] = get_workspace(kwargs["workspace"])
        del kwargs["workspace"]
        func(ctx, *args, **kwargs)

    return wrapped


def get_workspace(workspace):
    if workspace:
        workspace_path = path.Path(workspace)
    else:
        workspace_path = find_workspace_path()
    return tsrc.workspace.Workspace(workspace_path)
