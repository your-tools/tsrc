""" Common tools for tsrc commands """

import argparse
import os

from path import Path

import tsrc


def find_workspace_path() -> Path:
    """ Look for a workspace root somewhere in the upper directories
    hierarchy

    """
    head = os.getcwd()
    tail = "a truthy string"
    while tail:
        tsrc_path = os.path.join(head, ".tsrc")
        if os.path.isdir(tsrc_path):
            return Path(head)

        else:
            head, tail = os.path.split(head)
    raise tsrc.Error("Could not find current workspace")


def get_workspace(args: argparse.Namespace) -> tsrc.Workspace:
    if args.workspace_path:
        workspace_path = Path(args.workspace_path)
    else:
        workspace_path = find_workspace_path()
    return tsrc.Workspace(workspace_path)
