""" Entry point for tsrc push """

import re
import unidecode

from tsrc import ui
import tsrc.config
import tsrc.gitlab
import tsrc.git
import tsrc.cli


WIP_PREFIX = "WIP: "


def get_token():
    config = tsrc.config.read()
    return config["auth"]["gitlab"]["token"]


def get_project_name(repo_path):
    rc, out = tsrc.git.run_git(repo_path, "remote", "get-url", "origin", raises=False)
    if rc != 0:
        ui.fatal("Could not get url of 'origin' remote:", out)
    repo_url = out
    return project_name_from_url(repo_url)


def project_name_from_url(url):
    """
    >>> project_name_from_url('git@example.com:foo/bar.git')
    'foo/bar'
    >>> project_name_from_url('ssh://git@example.com:8022/foo/bar.git')
    'foo/bar'
    """
    # split everthing that is separated by a colon or a slash
    parts = re.split("[:/]", url)
    # join the last two parts
    res = "/".join(parts[-2:])
    # remove last `.git`
    if res.endswith(".git"):
        res = res[:-4]
    return res


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


def wipify(title):
    if not title.startswith(WIP_PREFIX):
        return WIP_PREFIX + title


def unwipify(title):
    if title.startswith(WIP_PREFIX):
        return title[len(WIP_PREFIX):]


class PushAction():
    def __init__(self, args, gl_helper=None):
        self.args = args
        self.gl_helper = gl_helper
        self.source_branch = None
        self.target_branch = None
        self.project_id = None
        self.project_name = None
        self.repo_path = None
        self.source_branch = None
        self.target_branch = None

    def main(self):
        self.prepare()
        self.push()
        self.handle_merge_request()

    def prepare(self):
        if not self.gl_helper:
            workspace = tsrc.cli.get_workspace(self.args)
            gitlab_url = workspace.get_gitlab_url()
            token = get_token()
            self.gl_helper = tsrc.gitlab.GitLabHelper(gitlab_url, token)

        self.repo_path = tsrc.git.get_repo_root()
        self.project_name = get_project_name(self.repo_path)
        self.project_id = self.gl_helper.get_project_id(self.project_name)

        current_branch = tsrc.git.get_current_branch(self.repo_path)
        self.source_branch = current_branch
        self.target_branch = self.args.target_branch

    def push(self):
        ui.info_2("Running git push")
        cmd = ["push", "-u", "origin", "%s:%s" % (self.source_branch, self.source_branch)]
        if self.args.force:
            cmd.append("--force")
        tsrc.git.run_git(self.repo_path, *cmd)

    def handle_merge_request(self):
        active_users = self.gl_helper.get_active_users()
        assignee = None
        if self.args.assignee:
            assignee = get_assignee(active_users, self.args.assignee)
            ui.info_2("Assigning to", assignee["name"])

        merge_request = self.ensure_merge_request()

        title = self.handle_title(merge_request)

        params = {
            "title": title,
            "target_branch": self.target_branch,
            "remove_source_branch": True,
        }
        if assignee:
            params["assignee_id"] = assignee["id"]

        self.gl_helper.update_merge_request(merge_request, **params)

        if self.args.accept:
            self.gl_helper.accept_merge_request(merge_request)

        ui.info(ui.green, "::",
                ui.reset, "See merge request at", merge_request["web_url"])

    def handle_title(self, merge_request):
        # If set from command line: use it
        if self.args.mr_title:
            return self.args.mr_title
        else:
            # Change the title if we need to
            title = merge_request["title"]
            if self.args.ready:
                return unwipify(title)
            if self.args.wip:
                return wipify(title)

    def ensure_merge_request(self):
        merge_request = self.gl_helper.find_opened_merge_request(self.project_id,
                                                                 self.source_branch)
        if merge_request:
            ui.info_2("Found existing merge request: !%s" % merge_request["iid"])
            return merge_request
        else:
            res = self.gl_helper.create_merge_request(self.project_id, self.source_branch,
                                                      title=self.source_branch,
                                                      target_branch=self.target_branch)
            return res


def main(args):
    push_action = PushAction(args)
    push_action.main()
