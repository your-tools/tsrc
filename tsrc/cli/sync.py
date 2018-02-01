""" tsrc sync """

import click
import ui

from tsrc.cli import workspace_cli


@click.command("sync")
@workspace_cli
def main(ctx):
    """ Synchronize workspace """
    workspace = ctx.obj["workspace"]
    workspace.update_manifest()
    workspace.load_manifest()
    active_groups = workspace.active_groups
    if active_groups:
        ui.info(ui.green, "*", ui.reset, "Using groups:", ",".join(active_groups))
    workspace.clone_missing()
    workspace.set_remotes()
    workspace.sync()
    workspace.copy_files()
    ui.info("Done", ui.check)
