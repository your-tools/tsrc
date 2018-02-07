""" tsrc log """
import sys

import click
import ui

import tsrc.git
from tsrc.cli import workspace_cli


@click.command("log")
@click.option("--from", metavar="<from>", required=True, is_flag=False)
@click.option("--to", metavar="<to>", is_flag=False, default="HEAD")
@workspace_cli
def main(ctx, *unused_args, **kwargs):
    """ Display changes between two git refs """
    # Using **kwargs here because 'from' is a reserved keyword
    from_ = kwargs["from"]
    to = kwargs["to"]
    workspace = ctx.obj["workspace"]
    workspace.load_manifest()
    all_ok = True
    for unused_index, repo, full_path in workspace.enumerate_repos():
        colors = ["green", "reset", "yellow", "reset", "bold blue", "reset"]
        log_format = "%m {}%h{} - {}%d{} %s {}<%an>{}"
        log_format = log_format.format(*("%C({})".format(x) for x in colors))
        cmd = ["log",
               "--color=always",
               "--pretty=format:%s" % log_format,
               "%s...%s" % (from_, to)]
        rc, out = tsrc.git.run_git(full_path, *cmd, raises=False)
        if rc != 0:
            all_ok = False
        if out:
            ui.info(ui.bold, repo.src)
            ui.info(ui.bold, "-" * len(repo.src))
            ui.info(out)
    if not all_ok:
        sys.exit(1)
