""" Entry point for tsrc status """
from collections import namedtuple

from tsrc import ui
import tsrc.cli


def collect_statuses(workspace, repos):
    # pylint: disable=invalid-name
    Status = namedtuple('Status', ['src', 'branch', 'dirty'])

    errors = list()
    result = list()

    if not repos:
        return errors, result

    num_repos = len(repos)
    max_len = max((len(x[0]) for x in repos))
    for i, src, full_path in workspace.enumerate_repos():
        ui.info_count(i, num_repos,
                      "Checking", src.ljust(max_len + 1), end="\r")
        try:
            branch = tsrc.git.get_current_branch(full_path)
        except tsrc.git.GitError as e:
            errors.append((src, e))
            continue

        dirty = tsrc.git.is_dirty(full_path)

        result.append(Status(src=src, branch=branch, dirty=dirty))

    ui.info("")
    return result, errors


def display_statuses(statuses, errors):
    if not statuses:
        return
    max_src = max((len(x[0]) for x in statuses))
    for status in statuses:
        message = (ui.green, "*", ui.reset, ui.bold, status.src.ljust(max_src),
                   ui.reset, ui.green, status.branch)
        if status.dirty:
            message = message + (ui.reset, ui.brown, "(dirty)")
        ui.info(*message)
    ui.info()

    if errors:
        ui.error("Errors when getting branch")
        for src, error in errors:
            ui.info("*", ui.bold, src, ui.reset, error.output)
        ui.info()


def main(args):
    workspace = tsrc.cli.get_workspace(args)
    manifest = workspace.load_manifest()
    repos = manifest.repos
    statuses, errors = collect_statuses(workspace, repos)
    display_statuses(statuses, errors)
