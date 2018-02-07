""" tsrc init """

import os

import click
import path
import ui

import tsrc.cli
import tsrc.workspace


@click.command("init")
@click.argument("url", nargs=1)
@click.option("-b", "--branch", metavar="<branch>", is_flag=False, default="master")
@click.option("-g", "--group", "groups", metavar="<group>", multiple=True)
@click.option("-s", "--shallow", is_flag=True)
@click.option("-w", "--workspace", metavar="<workspace>", is_flag=False)
def main(*, workspace, url, branch, groups, shallow):
    """ Init a new workspace """
    workspace_path = workspace or os.getcwd()
    workspace = tsrc.workspace.Workspace(path.Path(workspace_path))
    ui.info_1("Configuring workspace in", ui.bold, workspace_path)
    manifest_options = tsrc.workspace.options_from_dict(
        {
            "url": url,
            "branch": branch,
            "shallow": shallow,
            "groups": list(groups)
        }
    )

    workspace.configure_manifest(manifest_options)
    workspace.load_manifest()
    workspace.clone_missing()
    workspace.set_remotes()
    workspace.copy_files()
    ui.info("Done", ui.check)
