""" Entry point for tsrc foreach """

import subprocess
import sys

import tsrc.cli
from tsrc import ui


def main(args):
    workspace = tsrc.cli.get_workspace(args)
    errors = list()
    for _, src, full_path in workspace.enumerate_repos():
        ui.info_2("Running", "`%s`" % args.cmd_as_str, "on",
                  ui.bold, src)
        returncode = subprocess.call(args.cmd, cwd=full_path, shell=args.shell)
        if returncode != 0:
            errors.append(src)
    if errors:
        ui.info(ui.cross, ui.red, "foreach failed")
        for error in errors:
            ui.info("*", ui.bold, error)
        sys.exit(1)
    else:
        ui.info(ui.check, "All done")
