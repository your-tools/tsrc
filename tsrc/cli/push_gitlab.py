""" Entry point for tsrc push """

import argparse
import itertools
import textwrap
from typing import cast, List, Optional, Set  # noqa
import cli_ui as ui

import tsrc
from tsrc.gitlab_client.interface import Client, User, MergeRequest
from tsrc.cli.push import RepositoryInfo


WIP_PREFIX = "WIP: "


class UserNotFound(tsrc.Error):
    def __init__(self, username: str) -> None:
        self.username = username
        super().__init__("No user found with this username : %s" % self.username)


class AmbiguousUser(tsrc.Error):
    def __init__(self, query: str) -> None:
        self.query = query
        super().__init__("Found more that one user matching query: %s" % self.query)


class NoGitLabToken(tsrc.Error):
    def __init__(self) -> None:
        message = textwrap.dedent(
            """\
            Could not find GitLab token in tsrc config file
            Please check  https://tankerhq.github.io/tsrc/ref/formats/#tsrcyml_format
            for details\
            """
        )
        super().__init__(message)


class FeatureNotAvailable(tsrc.Error):
    def __init__(self, feature: str) -> None:
        self.name = feature
        message = (
            "The '%s' feature is not available on your GitLab installation" % self.name
        )
        super().__init__(message)


def get_token() -> str:
    config = tsrc.parse_tsrc_config()
    try:
        res = config["auth"]["gitlab"]["token"]
        return cast(str, res)
    except KeyError:
        raise NoGitLabToken() from None


def wipify(title: str) -> str:
    if not title.startswith(WIP_PREFIX):
        return WIP_PREFIX + title
    else:
        return title


def unwipify(title: str) -> str:
    if title.startswith(WIP_PREFIX):
        return title[len(WIP_PREFIX) :]
    else:
        return title


class MergeRequestProcessor:
    def __init__(
        self,
        repository_info: RepositoryInfo,
        args: argparse.Namespace,
        gitlab_client: Client,
    ) -> None:
        self.repository_info = repository_info
        self.gitlab_client = gitlab_client
        self.args = args

        project_name = repository_info.project_name

        self.project = self.gitlab_client.get_project(project_name)
        group_name = project_name.split("/")[0]

        self.group = self.gitlab_client.get_group(group_name)
        self.review_candidates = []  # type: List[User]

    def check_gitlab_feature(self, name: str) -> None:
        features = self.gitlab_client.get_features_list()
        if features is None:
            # Could not get the list of features for some reason,
            # (maybe current user is not a GitLab admin?)
            # so hope for the best
            return

        if name not in features:
            raise FeatureNotAvailable(name)

    def handle_reviewers(self) -> List[User]:
        self.check_gitlab_feature("multiple_merge_request_assignees")
        res = []
        for requested_username in self.args.reviewers:
            username = requested_username.strip()
            approver = self.get_reviewer_by_username(username)
            res.append(approver)
        return res

    def get_reviewer_by_username(self, username: str) -> User:
        in_project = self.project.search_members(username)
        if self.group:
            in_group = self.group.search_members(username)
        else:
            in_group = []
        candidates = []
        seen = set()  # type: Set[int]
        for user in itertools.chain(in_project, in_group):
            user_id = user.get_id()
            if user_id in seen:
                continue
            candidates.append(user)
            seen.add(user_id)
        if not candidates:
            raise UserNotFound(username)
        if len(candidates) > 1:
            raise AmbiguousUser(username)
        return candidates[0]

    def process(self) -> None:
        merge_request = self.ensure_merge_request()
        if self.args.close:
            ui.info_2(
                "Closing merge request", ui.bold, merge_request.get_short_description()
            )
            merge_request.close()
            merge_request.save()
            return

        merge_request.remove_source_branch()

        previous_title = merge_request.get_title()
        title = self.handle_title(merge_request)
        if title != previous_title:
            ui.info_3("Setting title to", ui.bold, title)
        merge_request.set_title(title)

        requested_target_branch = self.args.target_branch
        if requested_target_branch:
            ui.info_3("Setting target branch to", ui.bold, requested_target_branch)
            merge_request.set_target_branch(requested_target_branch)

        requested_assignee = self.args.assignee
        if requested_assignee:
            assignee = self.get_reviewer_by_username(requested_assignee)
            if assignee:
                ui.info_3("Assigning to", assignee.get_name())
                merge_request.set_assignee(assignee)

        if self.args.reviewers:
            approvers = self.handle_reviewers()
            if approvers:
                ui.info_3(
                    "Requesting approvals from",
                    ui.bold,
                    ", ".join(x.get_name() for x in approvers),
                )
                merge_request.set_approvers(approvers)

        merge_request.save()

        if self.args.accept:
            ui.info_3(
                "Accepting merge request",
                ui.bold,
                merge_request.get_short_description(),
            )
            merge_request.accept()

        ui.info(
            ui.green,
            "::",
            ui.reset,
            "See merge request at",
            ui.bold,
            merge_request.get_web_url(),
        )

    def handle_title(self, merge_request: MergeRequest) -> str:
        # If explicitely set, use it
        requested_title = self.args.title
        if requested_title:
            return requested_title  # type: ignore
        else:
            # Else change the title if we need to
            title = merge_request.get_title()  # type: str
            if self.args.ready:
                return unwipify(title)
            if self.args.wip:
                return wipify(title)
            return title

    def find_merge_request(self) -> Optional[MergeRequest]:
        remote_branch = self.repository_info.remote_branch
        res = self.project.find_merge_requests(
            state="opened", source_branch=remote_branch
        )
        if len(res) >= 2:
            raise tsrc.Error(
                "Found more than one opened merge request with the same branch"
            )
        if not res:
            return None
        return res[0]

    def create_merge_request(self) -> MergeRequest:
        requested_target_branch = self.args.target_branch
        if requested_target_branch:
            target_branch = requested_target_branch
        else:
            target_branch = self.project.get_default_branch()
        ui.info_2("Creating new merge request")
        remote_branch = self.repository_info.remote_branch
        return self.project.create_merge_request(
            source_branch=remote_branch,
            target_branch=target_branch,
            title=remote_branch,
        )

    def ensure_merge_request(self) -> MergeRequest:
        merge_request = self.find_merge_request()
        if merge_request:
            ui.info_2(
                "Found existing merge request",
                ui.bold,
                merge_request.get_short_description(),
            )
            return merge_request
        else:
            return self.create_merge_request()


def post_push(args: argparse.Namespace, repository_info: RepositoryInfo) -> None:
    from tsrc.gitlab_client.api_client import ApiClient

    token = get_token()
    login_url = repository_info.login_url
    # This will fail only if repository_info.login_url is None but we
    # somehowe detect the repository was using GitLab
    assert login_url

    client = ApiClient(login_url, token)
    processor = MergeRequestProcessor(repository_info, args, client)
    processor.process()
