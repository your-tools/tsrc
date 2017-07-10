""" Entry point for tsrc sync """

import sys

import tsrc
from tsrc import ui
import tsrc.cli


def display_bad_branches(on_bad_branch):
    if not on_bad_branch:
        return
    pad = max((len(x[0]) for x in on_bad_branch), default=0)
    ui.warning("Some projects are not on the correct branch")
    for (project, branch) in on_bad_branch:
        ui.info("*", ui.bold, project.ljust(pad + 1), ui.blue, branch)


def main(args):
    workspace = tsrc.cli.get_workspace(args)
    manifest = workspace.update_manifest()
    expected_branch = workspace.manifest_branch()
    workspace.clone_missing(manifest)
    errors = list()
    num_repos = len(manifest.repos)
    on_bad_branch = list()
    # Fetch then merge the remote tracking branch if it's
    # fast-forward
    # Display a warning if current branch is not the one
    # of the manifest
    for i, src, full_path in workspace.enumerate_repos():
        ui.info_count(i, num_repos, "Sync", ui.bold, src)
        current_branch = None
        try:
            current_branch = tsrc.git.get_current_branch(full_path)
            tsrc.git.run_git(full_path, "fetch", "--tags", "--prune", "origin")
            tsrc.git.run_git(full_path, "merge", "--ff-only", "@{u}")
        except tsrc.Error:
            errors.append(src)
        if current_branch and current_branch != expected_branch:
            on_bad_branch.append((src, current_branch))
    workspace.copy_files(manifest)
    display_bad_branches(on_bad_branch)
    if errors:
        ui.error(ui.cross, "Sync failed")
        for error in errors:
            ui.info("*", ui.bold, error)
        sys.exit(1)
    else:
        ui.info("Done", ui.check)
