""" Entry point for tsrc status """

import attr

from tsrc import ui
import tsrc.cli


# pylint: disable=too-few-public-methods
@attr.s
class Status:
    src = attr.ib()
    branch = attr.ib()
    dirty = attr.ib()


def collect_statuses(workspace):
    errors = list()
    result = list()
    repos = workspace.get_repos()

    if not repos:
        return errors, result

    num_repos = len(repos)
    max_len = max((len(x.src) for x in repos))
    for i, repo, full_path in workspace.enumerate_repos():
        ui.info_count(i, num_repos,
                      "Checking", repo.src.ljust(max_len + 1), end="\r")
        try:
            branch = tsrc.git.get_current_branch(full_path)
        except tsrc.git.GitError as e:
            errors.append((repo.src, e))
            continue

        dirty = tsrc.git.is_dirty(full_path)

        result.append(Status(src=repo.src, branch=branch, dirty=dirty))

    ui.info("")
    return result, errors


def display_statuses(statuses, errors):
    if not statuses:
        return
    max_src = max((len(x.src) for x in statuses))
    for status in statuses:
        message = (ui.green, "*", ui.reset, ui.bold, status.src.ljust(max_src),
                   ui.reset, ui.green, status.branch)
        if status.dirty:
            message = message + (ui.reset, ui.brown, "(dirty)")
        ui.info(*message)

    if errors:
        ui.info()
        ui.error("Errors when getting branch")
        for src, error in errors:
            ui.info("*", ui.bold, src, ui.reset, error.output)
        ui.info()


def main(args):
    workspace = tsrc.cli.get_workspace(args)
    workspace.load_manifest()
    statuses, errors = collect_statuses(workspace)
    display_statuses(statuses, errors)
