""" Entry point for tsrc log """

import sys

from tsrc import ui
import tsrc.cli
import tsrc.git


def main(args):
    workspace = tsrc.cli.get_workspace(args)
    all_ok = True
    for unused_index, src, full_path in workspace.enumerate_repos():
        colors = ["green", "reset", "yellow", "reset", "bold blue", "reset"]
        log_format = "%m {}%h{} - {}%d{} %s {}<%an>{}"
        log_format = log_format.format(*("%C({})".format(x) for x in colors))
        cmd = ["log",
               "--color=always",
               "--pretty=format:%s" % log_format,
               "%s...%s" % (args.from_, args.to)]
        rc, out = tsrc.git.run_git(full_path, *cmd, raises=False)
        if rc != 0:
            all_ok = False
        if out:
            ui.info(ui.bold, src)
            ui.info(ui.bold, "-" * len(src))
            ui.info(out)
    if not all_ok:
        sys.exit(1)
