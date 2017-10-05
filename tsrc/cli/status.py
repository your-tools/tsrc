""" Entry point for tsrc status """

import ui

import tsrc.cli


def describe_branch(git_status):
    if git_status.branch:
        return (ui.green, git_status.branch)
    elif git_status.sha1:
        return (ui.red, git_status.sha1)


def commit_string(number):
    if number == 1:
        return 'commit'
    else:
        return 'commits'


def describe_position(git_status):
    res = []
    if git_status.ahead != 0:
        res += (ui.blue, "+ %s %s", ui.reset) % (git_status.ahead, commit_string(git_status.ahead))
    if git_status.behind != 0:
        res += (ui.blue, "- %s %s", ui.reset) % (git_status.ahead, commit_string(git_status.ahead))
    return res


def describe_dirty(git_status):
    res = []
    if git_status.dirty:
        res = (ui.red, "dirty")
    return res


def describe(git_status):
    # Return a list of tokens suitable for ui.info()
    res = []
    res += describe_branch(git_status)
    res += describe_position(git_status)
    res += describe_dirty(git_status)
    return res


def display_statuses(workspace):
    for repo in workspace.repos:
        full_path = workspace.joinpath(repo.src)
        status = tsrc.git.get_status(full_path)
        ui.info(*describe(status))


def main(args):
    workspace = tsrc.cli.get_workspace(args)
    workspace.load_manifest()
    display_statuses(workspace)
