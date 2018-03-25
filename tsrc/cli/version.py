""" Entry point for tsrc version """

import pkg_resources

from path import Path
import ui

import tsrc.git


def get_details(location):
    # Maybe we are importing from a wheel or an egg:
    if not location.isdir():
        return ""
    # Maybe we are not in a git repo:
    try:
        status = tsrc.git.get_status(location)
    except tsrc.git.GitCommandError:
        return ""
    res = " - git: %s" % status.sha1
    if status.dirty:
        res += " (dirty)"
    return res


# pylint: disable=unused-argument
def main(args):
    tsrc_distribution = pkg_resources.get_distribution("tsrc")
    # pylint: disable=no-member
    version = tsrc_distribution.version
    message = "tsrc version %s" % version
    location = Path(tsrc_distribution.location)
    message += get_details(location)
    ui.info(message)
