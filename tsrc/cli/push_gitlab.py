""" Entry point for tsrc push """


import ui

import tsrc
import tsrc.config
import tsrc.gitlab
import tsrc.git
import tsrc.cli.push


WIP_PREFIX = "WIP: "


class NoUserMatching(tsrc.Error):
    def __init__(self, query):
        self.query = query
        super().__init__("No user found matching: %s" % self.query)


def get_token():
    config = tsrc.config.parse_tsrc_config()
    return config["auth"]["gitlab"]["token"]


def select_assignee(choices):
    return ui.ask_choice("Select an assignee", choices, func_desc=lambda x: x["name"])


def wipify(title):
    if not title.startswith(WIP_PREFIX):
        return WIP_PREFIX + title


def unwipify(title):
    if title.startswith(WIP_PREFIX):
        return title[len(WIP_PREFIX):]


class PushAction(tsrc.cli.push.PushAction):
    def __init__(self, repository_info, args, gl_helper=None):
        super().__init__(repository_info, args)
        self.gl_helper = gl_helper
        self.project_id = None

    def setup_service(self):
        if not self.gl_helper:
            workspace = tsrc.cli.get_workspace(self.args)
            workspace.load_manifest()
            gitlab_url = workspace.get_gitlab_url()
            token = get_token()
            self.gl_helper = tsrc.gitlab.GitLabHelper(gitlab_url, token)

        self.project_id = self.gl_helper.get_project_id(self.project_name)

    def handle_assignee(self):
        if not self.args.assignee:
            return None
        return self.find_assigne(self.args.assignee)

    def get_review_candidates(self, query):
        group_name = self.project_name.split("/")[0]
        project_members = self.gl_helper.get_project_members(self.project_id, query=query)
        group_members = self.gl_helper.get_group_members(group_name, query=query)
        # Concatenate and de-duplicate results:
        candidates = project_members + group_members
        res = list()
        seen = set()
        for user in candidates:
            user_name = user["name"]
            if user_name not in seen:
                seen.add(user_name)
                res.append(user)
        return res

    def find_assigne(self, query):
        candidates = self.get_review_candidates(query=query)
        if not candidates:
            raise NoUserMatching(query)
        if len(candidates) == 1:
            return candidates[0]
        return select_assignee(candidates)

    def post_push(self):
        merge_request = self.ensure_merge_request()
        if self.args.close:
            ui.info_2("Closing merge request #%s" % merge_request["iid"])
            self.gl_helper.update_merge_request(merge_request, state_event="close")
            return

        assignee = self.handle_assignee()
        if assignee:
            ui.info_2("Assigning to", assignee["name"])

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

    def find_merge_request(self):
        return self.gl_helper.find_opened_merge_request(
            self.project_id, self.remote_branch
        )

    def create_merge_request(self):
        return self.gl_helper.create_merge_request(
            self.project_id, self.remote_branch,
            title=self.remote_branch,
            target_branch=self.target_branch
        )

    def ensure_merge_request(self):
        merge_request = self.find_merge_request()
        if merge_request:
            ui.info_2("Found existing merge request: !%s" % merge_request["iid"])
            return merge_request
        else:
            return self.create_merge_request()
