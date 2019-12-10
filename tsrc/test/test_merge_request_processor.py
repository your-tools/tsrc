from typing import List, Sequence, Optional
import argparse
import pytest
from path import Path

import tsrc
from tsrc.gitlab_client.interface import (
    Group,
    Client,
    MergeRequest,
    Project,
    User,
    ProjectNotFound,
)

from tsrc.cli.push_gitlab import MergeRequestProcessor
from tsrc.cli.push import RepositoryInfo

GITLAB_URL = "http://gitlab.example.com"


class FakeUser(User):
    def __init__(self, id: int, name: str):
        self.name = name
        self.id = id

    def get_name(self) -> str:
        return self.name

    def get_id(self) -> int:
        return self.id


class FakeMergeRequest(MergeRequest):
    def __init__(self, *, source: str, target: str, title: str, id: int):
        self.source_branch = source
        self.target_branch = target
        self.title = title
        self.id = id
        self.should_remove_source_branch = False

    def save(self) -> None:
        self.saved = True

    def close(self) -> None:
        self.state = "closed"

    def accept(self) -> None:
        self.state = "accepted"

    def get_id(self) -> int:
        return self.id

    def get_title(self) -> str:
        return self.title

    def remove_source_branch(self) -> None:
        self.should_remove_source_branch = True

    def set_approvers(self, approvers: Sequence[User]) -> None:
        self.approvers = approvers

    def set_assignee(self, assignee: User) -> None:
        self.assignee = assignee

    def set_target_branch(self, branch: str) -> None:
        self.target_branch = branch

    def set_title(self, title: str) -> None:
        self.title = title

    def get_web_url(self) -> str:
        return "fake://merge_request/" + str(self.id)


class FakeProject(Project):
    def __init__(self, name: str):
        self.merge_requests = []  # type: List[FakeMergeRequest]
        self.members = []  # type: List[FakeUser]

        self.name = name
        self.default_branch = "master"

    def create_merge_request(
        self, *, source_branch: str, target_branch: str, title: str
    ) -> FakeMergeRequest:
        merge_request_id = len(self.merge_requests) + 1
        merge_request = FakeMergeRequest(
            source=source_branch, target=target_branch, title=title, id=merge_request_id
        )
        self.merge_requests.append(merge_request)
        return merge_request

    def get_default_branch(self) -> str:
        return self.default_branch

    def search_members(self, query: str) -> Sequence[User]:
        return [x for x in self.members if query in x.name]

    def find_merge_requests(
        self, *, state: str, source_branch: str
    ) -> Sequence[FakeMergeRequest]:
        # TODO
        return self.merge_requests

    def add_member(self, member: FakeUser) -> None:
        self.members.append(member)


class FakeGroup(Group):
    def __init__(self, name: str) -> None:
        self.members = []  # type: List[FakeUser]
        self.name = name

    def search_members(self, query: str) -> Sequence[User]:
        return [x for x in self.members if query in x.name]

    def add_member(self, member: FakeUser) -> None:
        self.members.append(member)


class FakeClient(Client):
    def __init__(self) -> None:
        self.features = []  # type: List[str]
        self.groups = []  # type: List[FakeGroup]
        self.projects = []  # type: List[FakeProject]

    def add_multiple_merge_request_assignees_feature(self) -> None:
        self.features.append("multiple_merge_request_assignees")

    def get_features_list(self) -> Sequence[str]:
        return self.features

    def get_group(self, name: str) -> Optional[FakeGroup]:
        for group in self.groups:
            if group.name == name:
                return group
        return None

    def get_project(self, project_name: str) -> FakeProject:
        for project in self.projects:
            if project.name == project_name:
                return project
        raise ProjectNotFound(project_name)

    def add_group(self, group_name: str) -> FakeGroup:
        group = FakeGroup(group_name)
        self.groups.append(group)
        return group

    def add_project(self, group_name: str, project_name: str) -> FakeProject:
        group = self.get_group(group_name)
        assert group
        project = FakeProject("{}/{}".format(group_name, project_name))
        self.projects.append(project)
        return project


@pytest.fixture
def repository_info() -> RepositoryInfo:
    return RepositoryInfo(
        project_name="owner/project",
        remote_name="orgin",
        url="git@gitlab.acme.com:owner/project",
        path=Path.getcwd(),
        current_branch="new-feature",
        tracking_ref="origin/new-feature",
        service="gitlab",
        login_url="https://gitlab.acme.org",
    )


@pytest.fixture
def client() -> FakeClient:
    client = FakeClient()
    client.add_group("owner")
    client.add_project("owner", "project")
    return client


class Context:
    def __init__(
        self,
        repository_info: RepositoryInfo,
        push_args: argparse.Namespace,
        client: FakeClient,
    ):
        self.repository_info = repository_info
        self.push_args = push_args
        self.client = client
        self.project = client.get_project("owner/project")
        group = client.get_group("owner")
        assert group
        self.group = group

    def run(self) -> None:
        merge_request_processor = MergeRequestProcessor(
            self.repository_info, self.push_args, self.client
        )
        merge_request_processor.process()


@pytest.fixture
def context(
    repository_info: RepositoryInfo, push_args: argparse.Namespace, client: FakeClient
) -> Context:
    return Context(repository_info, push_args, client)


def test_creating_merge_request_all_values_set(context: Context) -> None:
    """ Check we can create a pull request when using none of the default values
    in push_args
    """
    alice = FakeUser(name="alice", id=1)
    project = context.project
    project.members = [alice]

    context.push_args.assignee = "alice"
    context.push_args.target_branch = "next"
    context.push_args.title = "Best feature ever"
    context.run()

    (merge_request,) = project.merge_requests
    assert merge_request.assignee == alice
    assert merge_request.target_branch == "next"
    assert merge_request.title == "Best feature ever"
    assert merge_request.should_remove_source_branch


def test_creating_merge_request_uses_default_branch(context: Context) -> None:
    """ When the `--target` option is not set, check that the target of the created
    merge request is the default branch of the project
    """
    project = context.project
    project.default_branch = "stable"

    context.run()

    (merge_request,) = project.merge_requests
    assert merge_request.target_branch == "stable"


def test_can_set_multilpe_approvers_when_the_feature_exists(context: Context) -> None:
    """ When the `--reviewers` option is not set, and the merge request exists
    check that the list is updated.
    """
    client = context.client
    # Note: tsrc checks that the GitLab feature is present before using it,
    # so we have to explicitely configure the fake client there:
    client.add_multiple_merge_request_assignees_feature()

    project = context.project
    group = context.group

    alice = FakeUser(id=1, name="alice")
    bob = FakeUser(id=2, name="bob")

    # tsrc checks available members both in the project and in the group
    project.add_member(alice)
    group.add_member(bob)

    merge_request = project.create_merge_request(
        source_branch="new-feature", target_branch="master", title="New feature"
    )

    context.push_args.reviewers = ["alice", "bob"]
    context.run()

    assert merge_request.approvers == [alice, bob]


def test_proper_error_when_missing_gitlab_feature(context: Context) -> None:
    with pytest.raises(tsrc.cli.push_gitlab.FeatureNotAvailable) as e:
        context.push_args.reviewers = ["alice", "bob"]
        context.run()
    assert e.value.name == "multiple_merge_request_assignees"


def test_handle_ambiguous_assignee(context: Context) -> None:
    dupond = FakeUser(1, "dupond")
    dupont = FakeUser(2, "dupont")
    project = context.project
    project.add_member(dupond)
    project.add_member(dupont)

    with pytest.raises(tsrc.cli.push_gitlab.AmbiguousUser) as e:
        context.push_args.assignee = "dupon"
        context.run()
    assert e.value.query == "dupon"


def test_update_existing_merge_request(context: Context) -> None:
    project = context.project
    project.create_merge_request(
        source_branch="new-feature", target_branch="master", title="old title"
    )

    context.push_args.target_branch = "next"
    context.push_args.title = "Best feature ever"
    context.run()

    (merge_request,) = project.merge_requests
    assert merge_request.target_branch == "next"
    assert merge_request.title == "Best feature ever"


def test_close_merge_request(context: Context) -> None:
    project = context.project
    project.create_merge_request(
        source_branch="new-feature", target_branch="master", title="old title"
    )

    context.push_args.close = True
    context.run()

    (merge_request,) = project.merge_requests
    assert merge_request.state == "closed"


def test_do_not_change_target_branch(context: Context) -> None:
    project = context.project
    project.create_merge_request(
        source_branch="feat/1", target_branch="old-branch", title="old title"
    )

    context.run()

    (merge_request,) = project.merge_requests
    assert merge_request.target_branch == "old-branch"


def test_accept(context: Context) -> None:
    project = context.project
    project.create_merge_request(
        source_branch="new-feature", target_branch="master", title="New Feature"
    )

    context.push_args.accept = True
    context.run()

    (merge_request,) = project.merge_requests
    assert merge_request.state == "accepted"


def test_wipify(context: Context) -> None:
    """ When using `--wip` argument, the title should get prefixed by WIP: """
    project = context.project
    project.create_merge_request(
        source_branch="new-feature", target_branch="master", title="New Feature"
    )

    context.push_args.wip = True
    context.run()

    (merge_request,) = project.merge_requests
    assert merge_request.title == "WIP: New Feature"


def test_unwipify(context: Context) -> None:
    """ When using `--read` argument, the WIP prefix should get removed """
    project = context.project
    project.create_merge_request(
        source_branch="new-feature", target_branch="master", title="WIP: New Feature"
    )

    context.push_args.ready = True
    context.run()

    (merge_request,) = project.merge_requests
    assert merge_request.title == "New Feature"
