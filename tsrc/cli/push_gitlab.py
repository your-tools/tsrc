""" Entry point for tsrc push """


import argparse
from typing import List, Optional, Set

import ui

import tsrc
import tsrc.config
import tsrc.gitlab
from tsrc.gitlab import Assignee, GitLabHelper, MergeRequest
import tsrc.git
import tsrc.cli.push
from tsrc.cli.push import RepositoryInfo

_ = Set


WIP_PREFIX = "WIP: "


class NoUserMatching(tsrc.Error):
    def __init__(self, query: str) -> None:
        self.query = query
        super().__init__("No user found matching: %s" % self.query)


def get_token() -> str:
    config = tsrc.config.parse_tsrc_config()
    res = config["auth"]["gitlab"]["token"]  # type: str
    return res


def select_assignee(choices: List[Assignee]) -> Assignee:
    res = ui.ask_choice(
        "Select an assignee", choices,
        func_desc=lambda x: x["name"])  # type: Assignee
    return res


def wipify(title: str) -> str:
    if not title.startswith(WIP_PREFIX):
        return WIP_PREFIX + title
    else:
        return title


def unwipify(title: str) -> str:
    if title.startswith(WIP_PREFIX):
        return title[len(WIP_PREFIX):]
    else:
        return title


class PushAction(tsrc.cli.push.PushAction):
    def __init__(self, repository_info: RepositoryInfo, args:
                 argparse.Namespace, gl_helper: Optional[GitLabHelper] = None) -> None:
        super().__init__(repository_info, args)
        self.gl_helper = gl_helper
        self.project_id = None  # type: Optional[int]

    def setup_service(self) -> None:
        if not self.gl_helper:
            workspace = tsrc.cli.get_workspace(self.args)
            workspace.load_manifest()
            gitlab_url = workspace.get_gitlab_url()
            token = get_token()
            self.gl_helper = tsrc.gitlab.GitLabHelper(gitlab_url, token)

        assert self.project_name
        self.project_id = self.gl_helper.get_project_id(self.project_name)

    def handle_assignee(self) -> Optional[Assignee]:
        if not self.requested_assignee:
            return None
        return self.find_assigne(self.requested_assignee)

    def get_review_candidates(self, query: str) -> List[Assignee]:
        assert self.project_name
        group_name = self.project_name.split("/")[0]
        assert self.project_id
        assert self.gl_helper
        project_members = self.gl_helper.get_project_members(self.project_id, query=query)
        group_members = self.gl_helper.get_group_members(group_name, query=query)
        # Concatenate and de-duplicate results:
        candidates = project_members + group_members
        res = list()
        seen = set()  # type: Set[str]
        for user in candidates:
            user_name = user["name"]
            if user_name not in seen:
                seen.add(user_name)
                res.append(user)
        return res

    def find_assigne(self, query: str) -> Assignee:
        candidates = self.get_review_candidates(query=query)
        if not candidates:
            raise NoUserMatching(query)
        if len(candidates) == 1:
            return candidates[0]
        return select_assignee(candidates)

    def post_push(self) -> None:
        merge_request = self.ensure_merge_request()
        assert self.gl_helper
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
            "remove_source_branch": True,
        }
        if self.requested_target_branch:
            params["target_branch"] = self.requested_target_branch
        if assignee:
            params["assignee_id"] = assignee["id"]

        self.gl_helper.update_merge_request(merge_request, **params)  # type: ignore

        if self.args.accept:
            self.gl_helper.accept_merge_request(merge_request)

        ui.info(ui.green, "::",
                ui.reset, "See merge request at", merge_request["web_url"])

    def handle_title(self, merge_request: MergeRequest) -> str:
        # If explicitely set, use it
        if self.requested_title:
            return self.requested_title
        else:
            # Else change the title if we need to
            title = merge_request["title"]  # type: str
            if self.args.ready:
                return unwipify(title)
            if self.args.wip:
                return wipify(title)
            return title

    def find_merge_request(self) -> Optional[MergeRequest]:
        assert self.remote_branch
        assert self.project_id
        assert self.gl_helper
        return self.gl_helper.find_opened_merge_request(
            self.project_id, self.remote_branch
        )

    def create_merge_request(self) -> MergeRequest:
        assert self.project_id
        assert self.gl_helper
        if self.requested_target_branch:
            target_branch = self.requested_target_branch
        else:
            target_branch = self.gl_helper.get_default_branch(self.project_id)
        assert self.remote_branch
        return self.gl_helper.create_merge_request(
            self.project_id, self.remote_branch,
            title=self.remote_branch,
            target_branch=target_branch
        )

    def ensure_merge_request(self) -> MergeRequest:
        merge_request = self.find_merge_request()
        if merge_request:
            ui.info_2("Found existing merge request: !%s" % merge_request["iid"])
            return merge_request
        else:
            return self.create_merge_request()
