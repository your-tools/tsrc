from typing import Optional, List

import argparse
from path import Path
import pytest

from tsrc.github_client.interface import PullRequest, Repository, Client
from tsrc.cli.push import RepositoryInfo
from tsrc.cli.push_github import PullRequestProcessor


class FakePullRequest(PullRequest):
    def __init__(self, *, title: str, head: str, base: str, id: int):
        self.title = title
        self.head = head
        self.base = base
        self.id = id
        self.state = "open"
        self.requested_reviewers = []  # type: List[str]
        self.assigneed = None  # type: Optional[str]

    def update(self, *, title: Optional[str], base: Optional[str]) -> None:
        if title:
            self.title = title
        if base:
            self.base = base

    def merge(self) -> None:
        self.state = "merged"

    def close(self) -> None:
        self.state = "closed"

    def get_html_url(self) -> str:
        return "fakegithub://" + str(self.id)

    def get_number(self) -> int:
        return self.id

    def request_reviewers(self, reviewers: List[str]) -> None:
        self.requested_reviewers = reviewers

    def assign(self, assignee: str) -> None:
        self.assignee = assignee


class FakeRepository(Repository):
    def __init__(self, owner: str, name: str):
        self.name = name
        self.owner = owner
        self.pull_requests = []  # type: List[FakePullRequest]
        self.default_branch = "master"

    def create_pull_request(
        self, *, title: str, head: str, base: str
    ) -> FakePullRequest:
        pull_request_id = len(self.pull_requests) + 1
        pull_request = FakePullRequest(
            title=title, head=head, base=base, id=pull_request_id
        )
        self.pull_requests.append(pull_request)
        return pull_request

    def find_pull_requests(self, state: str, head: str) -> List[FakePullRequest]:
        return [x for x in self.pull_requests if x.state == state and x.head == head]

    def get_default_branch(self) -> str:
        return self.default_branch


class FakeClient(Client):
    def __init__(self) -> None:
        self.repositories = []  # type: List[FakeRepository]

    def get_repository(self, owner: str, name: str) -> FakeRepository:
        for repository in self.repositories:
            if repository.owner == owner and repository.name == name:
                return repository
        assert False


@pytest.fixture
def repository_info() -> RepositoryInfo:
    return RepositoryInfo(
        project_name="owner/project",
        remote_name="orgin",
        url="git@github.com:owner/project",
        path=Path.getcwd(),
        current_branch="new-feature",
        tracking_ref="origin/new-feature",
        service="github",
        login_url="https://github.com",
    )


@pytest.fixture
def client() -> FakeClient:
    repository = FakeRepository("owner", "project")
    client = FakeClient()
    client.repositories = [repository]
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
        self.repository = client.get_repository("owner", "project")

    def run(self) -> None:
        pull_request_processor = PullRequestProcessor(
            self.repository_info, self.push_args, self.client
        )
        pull_request_processor.process()


@pytest.fixture
def context(
    repository_info: RepositoryInfo, push_args: argparse.Namespace, client: FakeClient
) -> Context:
    return Context(repository_info, push_args, client)


def test_create_pull_request_all_values_set(context: Context) -> None:
    """ Check we can create a pull request when using none of the default values
    in push_args
    """
    context.push_args.assignee = "alice"
    context.push_args.reviewers = ["bob", "charlie"]
    context.push_args.target_branch = "next"
    context.push_args.title = "Best feature ever"
    context.run()

    repository = context.repository
    (pull_request,) = repository.pull_requests
    assert pull_request.assignee == "alice"
    assert pull_request.requested_reviewers == ["bob", "charlie"]
    assert pull_request.base == "next"
    assert pull_request.title == "Best feature ever"


def test_create_pull_request_using_remote_branch(context: Context) -> None:
    """ When running `tsrc push local:remote`, we want the head of the pull request
    to be `remote`, not `local`
    """
    repository_info = context.repository_info
    repository_info.current_branch = "local"
    repository_info.tracking_ref = "origin/remote"

    context.run()

    repository = context.repository
    (pull_request,) = repository.pull_requests
    assert pull_request.head == "remote"


def test_update_base(context: Context) -> None:
    """ When using `tsrc push --target stable` and a pull requests already exists with a
    `master` base, we want to keep the existing title, but change the base

    """
    repository = context.repository
    repository.create_pull_request(
        title="Existing title", head="new-feature", base="master"
    )

    context.push_args.target_branch = "stable"
    context.run()

    (pull_request,) = repository.pull_requests
    assert pull_request.base == "stable"


def test_merge(context: Context) -> None:
    """ When using `tsrc push --merge` and a pull request already exists we want
    to find it and merge it.

    """
    repository = context.repository

    closed_pr = repository.create_pull_request(
        title="Closed PR", head="new-feature", base="master"
    )
    closed_pr.close()

    opened_pr = repository.create_pull_request(
        title="Original title", head="new-feature", base="master"
    )
    repository.create_pull_request(
        title="Wrong base", head="other-branch", base="master"
    )

    context.push_args.merge = True
    context.run()

    assert opened_pr.state == "merged"
    assert opened_pr.title == "Original title"


def test_close(context: Context) -> None:
    """ When using `tsrc push --close` and a pull request already exists we want
    to find it and close it.

    """
    repository = context.repository
    opened_pr = repository.create_pull_request(
        title="Opened PR", head="new-feature", base="master"
    )

    context.push_args.close = True
    context.run()

    assert opened_pr.state == "closed"
