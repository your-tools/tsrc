from typing import Any, Optional, Sequence

from gitlab import Gitlab
from gitlab.exceptions import GitlabGetError

from .interface import User, MergeRequest, Project, Group, Client
import tsrc

MAX_USERS = 100


class TooManyUsers(tsrc.Error):
    def __init__(self, max_users: int) -> None:
        self.max_users = max_users
        super().__init__("More than %s users found" % self.max_users)


class GitLabUser(User):
    def __init__(self, gl_user: Any):
        self.gl_user = gl_user

    def get_id(self) -> int:
        return self.gl_user.id  # type: ignore

    def get_name(self) -> str:
        return self.gl_user.name  # type: ignore


class GitLabMergeRequest(MergeRequest):
    def __init__(self, gl_merge_request: Any):
        self.gl_merge_request = gl_merge_request

    def get_id(self) -> int:
        return self.gl_merge_request.iid  # type: ignore

    def get_web_url(self) -> str:
        return self.gl_merge_request.web_url  # type: ignore

    def get_title(self) -> str:
        return self.gl_merge_request.title  # type: ignore

    def set_title(self, title: str) -> None:
        self.gl_merge_request.title = title

    def set_target_branch(self, target_branch: str) -> None:
        self.gl_merge_request.target_branch = target_branch

    def set_assignee(self, assignee: User) -> None:
        assignee_id = assignee.get_id()
        self.gl_merge_request.assignee_id = assignee_id

    def set_approvers(self, approvers: Sequence[User]) -> None:
        self.gl_merge_request.approvals.set_approvers([x.get_id() for x in approvers])

    def remove_source_branch(self) -> None:
        self.gl_merge_request.remove_source_branch = True

    def accept(self) -> None:
        self.gl_merge_request.merge(merge_when_pipeline_succeeds=True)

    def close(self) -> None:
        self.gl_merge_request.close()

    def save(self) -> None:
        self.gl_merge_request.save()


class GitLabProject(Project):
    def __init__(self, gl_project: Any):
        self.gl_project = gl_project

    def find_merge_requests(
        self, *, state: str, source_branch: str
    ) -> Sequence[MergeRequest]:
        gl_merge_requests = self.gl_project.mergerequests.list(
            state="opened", source_branch=source_branch, all=True
        )
        return [GitLabMergeRequest(x) for x in gl_merge_requests]

    def get_default_branch(self) -> str:
        return self.gl_project.default_branch  # type: ignore

    def create_merge_request(
        self, *, source_branch: str, target_branch: str, title: str
    ) -> GitLabMergeRequest:
        gl_merge_request = self.gl_project.mergerequests.create(
            {
                "source_branch": source_branch,
                "target_branch": target_branch,
                "title": title,
            }
        )
        return GitLabMergeRequest(gl_merge_request)

    def search_members(self, query: str) -> Sequence[User]:
        return get_users_matching(self.gl_project.members, query)


class GitLabGroup(Group):
    def __init__(self, gl_group: Any):
        self.gl_group = gl_group

    def search_members(self, query: str) -> Sequence[User]:
        return get_users_matching(self.gl_group.members, query)


def get_users_matching(members: Any, query: str) -> Sequence[User]:
    res = members.list(active=True, query=query, per_page=100, as_list=False)
    if res.next_page:
        raise TooManyUsers(100)
    return [GitLabUser(x) for x in res]


class ApiClient(Client):
    def __init__(self, login_url: str, token: str):
        self.gl_api = Gitlab(login_url, private_token=token)

    def get_group(self, group_name: str) -> Optional[Group]:
        try:
            gl_group = self.gl_api.groups.get(group_name)
            return GitLabGroup(gl_group)
        except GitlabGetError as e:
            if e.response_code == 404:
                return None
            else:
                raise

    def get_features_list(self) -> Optional[Sequence[str]]:
        try:
            gl_features = self.gl_api.features.list()
        except GitlabGetError as e:
            if e.response_code == 403:
                return None
        return [x.name for x in gl_features]

    def get_project(self, name: str) -> Project:
        gl_project = self.gl_api.projects.get(name)
        return GitLabProject(gl_project)
