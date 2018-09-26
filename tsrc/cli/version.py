""" Entry point for tsrc version """

import argparse
import pkg_resources

from path import Path
import ui

import tsrc
import tsrc.git


def get_details(location: Path) -> str:
    # Maybe we are importing from a wheel or an egg:
    if not location.isdir():
        return ""
    # Maybe we are not in a git repo:
    try:
        status = tsrc.git.get_status(location)
    except tsrc.git.CommandError:
        return ""
    res = " - git: %s" % status.sha1
    if status.dirty:
        res += " (dirty)"
    return res


def main(args: argparse.Namespace) -> None:
    tsrc_distribution = pkg_resources.get_distribution("tsrc")
    version = tsrc_distribution.version
    message = "tsrc version %s" % version
    location = Path(tsrc_distribution.location)
    message += get_details(location)
    ui.info(message)
