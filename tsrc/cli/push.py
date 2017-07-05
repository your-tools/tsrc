""" Entry point for tsrc push """

import argparse
import unidecode

import path

from tcommon import ui
import tcommon.gitlab
import tsrc.git
import tsrc.cli


def push(repo_path, branch, *, force=False):
    ui.info_2("Running git push")
    cmd = ["push", "-u", "origin", "%s:%s" % (branch, branch)]
    if force:
        cmd.append("--force")
    tsrc.git.run_git(repo_path, *cmd)


def get_project_id(workspace, repo_path):
    repo_src = repo_path.relpath(workspace.root_path)
    repo_url = workspace.get_url(repo_src)
    project_name = tcommon.gitlab.project_name_form_url(repo_url)
    project_id = tcommon.gitlab.get_project_id(project_name)
    return project_id


def main(args):
    workspace = tsrc.cli.get_workspace(args)
    repo_path = tsrc.git.get_repo_root()

    current_branch = tsrc.git.get_current_branch(repo_path)
    push(repo_path, current_branch, force=args.force)

    source_branch = current_branch
    target_branch = args.target_branch
    project_id = get_project_id(workspace, repo_path)
    active_users = tcommon.gitlab.get_active_users()

    assignee = None
    if args.assignee:
        assignee = get_assignee(active_users, args.assignee)

    merge_request = tcommon.gitlab.ensure_merge_request(project_id, source_branch,
                                                        target_branch=target_branch,
                                                        title=args.mr_title,
                                                        assignee=assignee)
    if args.accept:
        tcommon.gitlab.accept_merge_request(merge_request)

    ui.info(ui.green, "::",
            ui.reset, "See merge request at", merge_request["web_url"])


def get_assignee(users, pattern):
    def sanitize(string):
        string = unidecode.unidecode(string)
        string = string.lower()
        return string
    # Sanitize both the list of names and the input
    usernames = [x["name"] for x in users]
    sanitized_names = [sanitize(x) for x in usernames]
    sanitized_pattern = sanitize(pattern)
    matches = list()
    for user, sanitized_name in zip(users, sanitized_names):
        if sanitized_pattern in sanitized_name:
            matches.append(user)
    if not matches:
        message = ui.did_you_mean("No user found matching %s" % pattern,
                                  pattern, usernames)

        raise tcommon.Error(message)
    if len(matches) > 1:
        ambiguous_names = [x["name"] for x in matches]
        raise tcommon.Error("Found several users matching %s: %s" %
                            (pattern, ", ".join(ambiguous_names)))

    if len(matches) == 1:
        return matches[0]


def test_mr_creation():
    """ Integration testing. This creates a real MR, handle with care """

    parser = argparse.ArgumentParser()
    parser.add_argument("working_path", type=path.Path)
    parser.add_argument("project_name")
    parser.add_argument("-b", "--branch", required=True)
    parser.add_argument("-a", "--assignee")
    args = parser.parse_args()
    working_path = args.working_path
    project_name = args.project_name
    branch = args.branch

    active_users = tcommon.gitlab.get_active_users()
    assignee = None
    if args.assignee:
        assignee = get_assignee(active_users, args.assignee)

    tsrc.git.run_git(working_path, "checkout", "-B", branch)
    tsrc.git.run_git(working_path, "commit", "-m", "test", "--allow-empty")
    tsrc.git.run_git(working_path, "push", "-u", "origin", "%s:%s" % (branch, branch))
    project_id = tcommon.gitlab.get_project_id(project_name)
    merge_request = tcommon.gitlab.ensure_merge_request(project_id, branch, assignee=assignee)
    tcommon.gitlab.accept_merge_request(merge_request)
    print(merge_request["web_url"])


if __name__ == "__main__":
    test_mr_creation()
