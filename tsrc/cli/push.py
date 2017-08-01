""" Entry point for tsrc push """

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


def get_project_name(*, url, prefix):
    if not url.startswith(prefix):
        message = "Could not get project name name.\n"
        message += "(prefix: %s, url: %s) " % (prefix, url)
        raise tsrc.Error(message)
    res = url[len(prefix):]
    if res.endswith(".git"):
        return res[:-4]


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
        workspace = tsrc.cli.get_workspace(self.args)
        gitlab_url = workspace.get_gitlab_url()
        clone_prefix = workspace.get_clone_prefix()

        if not self.gl_helper:
            token = get_token()
            self.gl_helper = tsrc.gitlab.GitLabHelper(gitlab_url, token)

        self.repo_path = tsrc.git.get_repo_root()
        project_url = tsrc.git.get_origin_url(self.repo_path)
        self.project_name = get_project_name(url=project_url, prefix=clone_prefix)
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
