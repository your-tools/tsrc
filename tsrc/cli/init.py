""" Entry point for `tsrc init` """
import os

import path
import ui

import tsrc.workspace


def main(args):
    workspace_path = args.workspace_path or os.getcwd()
    workspace = tsrc.workspace.Workspace(path.Path(workspace_path))
    ui.info_1("Configuring workspace in", ui.bold, workspace_path)
    workspace.configure_manifest(url=args.manifest_url, branch=args.branch, groups=args.groups)
    workspace.load_manifest()
    workspace.clone_missing()
    workspace.set_remotes()
    workspace.copy_files()
    ui.info("Done", ui.check)
