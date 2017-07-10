""" Entry point for tsrc push """

import unidecode

from tsrc import ui
import tsrc.gitlab
import tsrc.git
import tsrc.cli


WIP_PREFIX = "WIP: "


def get_project_name(repo_path):
    rc, out = tsrc.git.run_git(repo_path, "remote", "get-url", "origin", raises=False)
    if rc != 0:
        ui.fatal("Could not get url of 'origin' remote:", out)
    repo_url = out
    return project_name_from_url(repo_url)


def project_name_from_url(url):
    """
    >>> project_name_from_url(git@example.com:foo/bar.git)
    'foo/bar'
    """
    return "/".join(url.split("/")[-2:]).replace(".git", "")


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

        raise tsrc.Error(message)
    if len(matches) > 1:
        ambiguous_names = [x["name"] for x in matches]
        raise tsrc.Error("Found several users matching %s: %s" %
                         (pattern, ", ".join(ambiguous_names)))

    if len(matches) == 1:
        return matches[0]


def ensure_merge_request(project_id, source_branch, target_branch):
    merge_request = tsrc.gitlab.find_opened_merge_request(project_id, source_branch)
    if merge_request:
        ui.info_2("Found existing merge request: !%s" % merge_request["iid"])
        return merge_request
    else:
        res = tsrc.gitlab.create_merge_request(project_id, source_branch,
                                               title=source_branch,
                                               target_branch=target_branch)
        return res


def wipify(title):
    if not title.startswith(WIP_PREFIX):
        return WIP_PREFIX + title


def unwipify(title):
    if title.startswith(WIP_PREFIX):
        return title[len(WIP_PREFIX):]


def handle_title(args, merge_request):
    # If set from command line: use it
    if args.mr_title:
        return args.mr_title
    else:
        # Change the title if we need to
        title = merge_request["title"]
        if args.ready:
            return unwipify(title)
        if args.wip:
            return wipify(title)


def handle_merge_request(args, repo_path, current_branch):
    source_branch = current_branch
    target_branch = args.target_branch
    project_name = get_project_name(repo_path)
    project_id = tsrc.gitlab.get_project_id(project_name)

    active_users = tsrc.gitlab.get_active_users()
    assignee = None
    if args.assignee:
        assignee = get_assignee(active_users, args.assignee)

    merge_request = ensure_merge_request(project_id, source_branch=source_branch,
                                         target_branch=args.target_branch)

    title = handle_title(args, merge_request)
    params = {
        "title": title,
        "target_branch": target_branch,
        "remove_source_branch": True,
    }
    if assignee:
        params["assignee_id"] = assignee["id"]

    tsrc.gitlab.update_merge_request(merge_request, **params)

    if args.accept:
        tsrc.gitlab.accept_merge_request(merge_request)

    ui.info(ui.green, "::",
            ui.reset, "See merge request at", merge_request["web_url"])


def push(args, repo_path, branch):
    ui.info_2("Running git push")
    cmd = ["push", "-u", "origin", "%s:%s" % (branch, branch)]
    if args.force:
        cmd.append("--force")
    tsrc.git.run_git(repo_path, *cmd)


def main(args):
    repo_path = tsrc.git.get_repo_root()

    current_branch = tsrc.git.get_current_branch(repo_path)

    push(args, repo_path, current_branch)
    handle_merge_request(args, repo_path, current_branch)
