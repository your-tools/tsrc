import argparse
from typing import Any

import github3
import mock
from path import Path
import pytest

import tsrc
from tsrc.test.helpers.cli import CLI
from tsrc.cli.push import RepositoryInfo
from tsrc.cli.push_github import PushAction


@pytest.fixture
def github_mock() -> Any:
    # FIXME: a type that contains github3.GitHub plus other methods ?
    github_mock = mock.create_autospec(github3.GitHub, instance=True)
    return github_mock


def execute_push(repo_path: Path, push_args: argparse.Namespace, github_mock: Any) -> None:
    repository_info = RepositoryInfo()
    repository_info.read_working_path(repo_path)
    push_action = PushAction(repository_info, push_args, github_api=github_mock)
    push_action.execute()


def test_create(repo_path: Path, tsrc_cli: CLI, github_mock: Any,
                push_args: argparse.Namespace) -> None:
    mock_repo = mock.Mock()
    mock_repo.pull_requests.return_value = list()
    mock_repo.owner = mock.Mock()
    mock_repo.owner.login = "owner"
    mock_repo.name = "project"
    github_mock.repository.return_value = mock_repo
    mock_pr = mock.Mock()
    mock_repo.create_pull.return_value = mock_pr
    mock_repo.default_branch = "devel"
    mock_pr.html_url = "https://github.com/owner/project/pull/42"
    mock_pr.number = 42
    mock_issue = mock.Mock()

    tsrc.git.run(repo_path, "checkout", "-b", "new-feature")
    tsrc.git.run(repo_path, "commit", "--message", "new feature", "--allow-empty")
    push_args.title = "new feature"
    push_args.assignee = "assignee1"
    push_args.reviewers = ["reviewer1", "reviewer2"]

    mock_repo._build_url.return_value = "request_url"
    mock_repo._post.return_value = mock.Mock(status_code=201)
    mock_repo.issue.return_value = mock_issue

    execute_push(repo_path, push_args, github_mock)

    mock_repo.create_pull.assert_called_with("new feature", "devel", "new-feature")
    mock_repo.pull_requests.assert_called_with()
    mock_repo.issue.assert_called_with(42)
    mock_issue.assign.assert_called_with("assignee1")
    mock_repo._build_url.assert_called_with(
        "repos", "owner", "project", "pulls", 42, "requested_reviewers")
    mock_repo._post.assert_called_with(
        "request_url", data={"reviewers": ["reviewer1", "reviewer2"]})


def test_push_custom_tracked_branch(repo_path: Path, push_args: argparse.Namespace,
                                    github_mock: Any) -> None:
    stub_repo = mock.Mock()
    stub_repo.pull_requests.return_value = list()
    stub_repo.default_branch = "master"
    github_mock.repository.return_value = stub_repo
    tsrc.git.run(repo_path, "checkout", "-b", "local")
    tsrc.git.run(repo_path, "push", "-u", "origin", "local:remote")

    push_args.title = "new feature"
    execute_push(repo_path, push_args, github_mock)
    stub_repo.create_pull.assert_called_with("new feature", "master", "remote")


def test_update_target_and_title(repo_path: Path, push_args: argparse.Namespace,
                                 github_mock: Any) -> None:
    opened_pr = mock.Mock()
    opened_pr.number = 2
    opened_pr.state = "open"
    opened_pr.head.ref = "new-feature"
    opened_pr.base.ref = "devel"
    opened_pr.title = "old title"
    opened_pr.html_url = "https://github.com/foo/bar/pull/42"

    stub_repo = mock.Mock()
    stub_repo.pull_requests.return_value = [opened_pr]
    stub_repo.default_branch = "master"
    github_mock.repository.return_value = stub_repo
    tsrc.git.run(repo_path, "checkout", "-b", "new-feature")
    tsrc.git.run(repo_path, "push", "-u", "origin", "new-feature")

    push_args.target_branch = "master"
    push_args.title = "new title"
    execute_push(repo_path, push_args, github_mock)
    opened_pr.update.assert_called_with(title="new title", base="master")


def test_merge(repo_path: Path, tsrc_cli: CLI, github_mock: Any,
               push_args: argparse.Namespace) -> None:
    closed_pr = mock.Mock()
    closed_pr.number = 1
    closed_pr.state = "closed"
    closed_pr.head.ref = "new-feature"

    opened_pr = mock.Mock()
    opened_pr.number = 2
    opened_pr.state = "open"
    opened_pr.head.ref = "new-feature"
    opened_pr.html_url = "https://github.com/foo/bar/pull/42"

    opened_pr_wrong_branch = mock.Mock()
    opened_pr_wrong_branch.number = 3
    opened_pr_wrong_branch.state = "open"
    opened_pr_wrong_branch.head.ref = "wrong-branch"

    mock_repo = mock.Mock()
    mock_repo.pull_requests.return_value = [closed_pr, opened_pr, opened_pr_wrong_branch]
    github_mock.repository.return_value = mock_repo

    tsrc.git.run(repo_path, "checkout", "-b", "new-feature")
    tsrc.git.run(repo_path, "commit", "--message", "new feature", "--allow-empty")
    push_args.merge = True
    execute_push(repo_path, push_args, github_mock)

    mock_repo.create_pull.assert_not_called()
    opened_pr.merge.assert_called_with()


def test_close(repo_path: Path, tsrc_cli: CLI,
               github_mock: Any, push_args: argparse.Namespace) -> None:
    opened_pr = mock.Mock()
    opened_pr.number = 2
    opened_pr.state = "open"
    opened_pr.head.ref = "new-feature"
    opened_pr.html_url = "https://github.com/foo/bar/pull/42"

    mock_repo = mock.Mock()
    mock_repo.pull_requests.return_value = [opened_pr]
    github_mock.repository.return_value = mock_repo

    tsrc.git.run(repo_path, "checkout", "-b", "new-feature")
    tsrc.git.run(repo_path, "commit", "--message", "new feature", "--allow-empty")

    push_args.merge = True
    push_args.close = True
    execute_push(repo_path, push_args, github_mock)

    opened_pr.close.assert_called_with()
