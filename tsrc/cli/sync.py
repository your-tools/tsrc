""" Entry point for tsrc sync """

import sys

import tsrc
from tsrc import ui
import tsrc.cli


def display_bad_branches(on_bad_branch):
    if not on_bad_branch:
        return
    ui.warning("Some projects are not on the correct branch")
    headers = ("project", "actual", "expected")
    data = [
        ((ui.bold, name), (ui.red, actual), (ui.green, expected)) for
        (name, actual, expected) in on_bad_branch
    ]
    ui.info_table(data, headers=headers)


def main(args):
    workspace = tsrc.cli.get_workspace(args)
    manifest = workspace.update_manifest()
    workspace.clone_missing(manifest)
    errors = list()
    num_repos = len(manifest.repos)
    on_bad_branch = list()
    # Fetch then merge the remote tracking branch if it's
    # fast-forward
    # Display a warning if current branch is not the one
    # of the manifest
    for i, repo, full_path in workspace.enumerate_repos():
        ui.info_count(i, num_repos, "Sync", ui.bold, repo.src)
        current_branch = None
        try:
            current_branch = tsrc.git.get_current_branch(full_path)
            tsrc.git.run_git(full_path, "fetch", "--tags", "--prune", "origin")
            tsrc.git.run_git(full_path, "merge", "--ff-only", "@{u}")
        except tsrc.Error:
            errors.append(repo.src)
        if current_branch and current_branch != repo.branch:
            on_bad_branch.append((repo.src, current_branch, repo.branch))
    workspace.copy_files(manifest)
    display_bad_branches(on_bad_branch)
    if errors:
        ui.error(ui.cross, "Sync failed")
        for error in errors:
            ui.info("*", ui.bold, error)
        sys.exit(1)
    else:
        ui.info("Done", ui.check)
