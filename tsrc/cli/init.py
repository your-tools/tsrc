""" Entry point for `tsrc init` """
import os

import path

from tsrc import ui
import tsrc.workspace


def main(args):
    workspace_path = args.workspace_path or os.getcwd()
    workspace = tsrc.workspace.Workspace(path.Path(workspace_path))
    ui.info_1("Creating new workspace in", ui.bold, workspace_path)
    workspace.init_manifest(args.manifest_url, branch=args.branch)
    manifest = workspace.load_manifest()
    workspace.clone_missing(manifest)
    workspace.set_remotes()
    workspace.copy_files(manifest)
    ui.info("Done", ui.check)
