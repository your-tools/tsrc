""" Entry point for tsrc status """

import argparse
from typing import List, Tuple
import shutil

import ui

import tsrc
import tsrc.cli
import tsrc.git


def describe_branch(git_status: tsrc.git.Status) -> List[str]:
    res = list()  # type: List[str]
    if git_status.branch:
        res += [ui.green, git_status.branch]
    elif git_status.sha1:
        res += [ui.red, git_status.sha1]
    if git_status.tag:
        res += [ui.reset, ui.brown, "on", git_status.tag]
    return res


def commit_string(number: int) -> str:
    if number == 1:
        return 'commit'
    else:
        return 'commits'


def describe_position(git_status: tsrc.git.Status) -> List[str]:
    res = []  # type: List[str]
    if git_status.ahead != 0:
        up = ui.Symbol("↑", "+")
        n_commits = commit_string(git_status.ahead)
        ahead_desc = "{}{} {}".format(up.as_string, git_status.ahead, n_commits)
        res += [ui.blue, ahead_desc, ui.reset]
    if git_status.behind != 0:
        down = ui.Symbol("↓", "-")
        n_commits = commit_string(git_status.behind)
        behind_desc = "{}{} {}".format(down.as_string, git_status.behind, n_commits)
        res += [ui.blue, behind_desc, ui.reset]
    return res


def describe_dirty(git_status: tsrc.git.Status) -> List[str]:
    res = []  # type: List[str]
    if git_status.dirty:
        res += [ui.red, "(dirty)"]
    return res


def describe(git_status: tsrc.git.Status) -> List[str]:
    # Return a list of tokens suitable for ui.info()
    res = []  # type: List[str]
    res += describe_branch(git_status)
    res += describe_position(git_status)
    res += describe_dirty(git_status)
    return res


def collect_statuses(workspace: tsrc.Workspace) -> List[Tuple[str, tsrc.git.Status]]:
    result = list()  # type: List[Tuple[str, tsrc.git.Status]]
    repos = workspace.get_repos()

    if not repos:
        return result

    num_repos = len(repos)
    max_len = max((len(x.src) for x in repos))
    for i, repo, full_path in workspace.enumerate_repos():
        ui.info_count(i, num_repos,
                      "Checking", repo.src.ljust(max_len + 1), end="\r")
        status = tsrc.git.get_status(full_path)
        result.append((repo.src, status))

    terminal_size = shutil.get_terminal_size()
    ui.info(" " * terminal_size.columns, end="\r")
    return result


def display_statuses(statuses: List[Tuple[str, tsrc.git.Status]]) -> None:
    if not statuses:
        return
    max_src = max((len(x[0]) for x in statuses))
    for src, status in statuses:
        message = [ui.green, "*", ui.reset, src.ljust(max_src)]
        message += describe(status)
        ui.info(*message)


def main(args: argparse.Namespace) -> None:
    workspace = tsrc.cli.get_workspace(args)
    workspace.load_manifest()
    statuses = collect_statuses(workspace)
    display_statuses(statuses)
