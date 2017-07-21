""" Entry point for tsrc version """

import pkg_resources

import path

from tsrc import ui
import tsrc.git


# pylint: disable=unused-argument
def main(args):
    tsrc_distribution = pkg_resources.get_distribution("tsrc")
    # pylint: disable=no-member
    version = tsrc_distribution.version
    location = path.Path(tsrc_distribution.location)
    dirty = False
    short_hash = None
    rc, out = tsrc.git.run_git(location, "rev-parse", "--short", "HEAD", raises=False)
    if rc == 0:
        short_hash = out
        dirty = tsrc.git.is_dirty(location)
    message = "tsrc version %s" % version
    if short_hash:
        message += " - git: %s" % short_hash
        if dirty:
            message += " (dirty)"
    ui.info(message)
