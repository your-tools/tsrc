import types

import github3
import mock
import pytest

import tsrc.git
from tsrc.cli.push import RepositoryInfo
from tsrc.cli.push_github import PushAction
from tsrc.test.helpers.push import repo_path, push_args


@pytest.fixture
def github_mock():
    github_mock = mock.create_autospec(github3.GitHub, instance=True)
    return github_mock


def execute_push(repo_path, push_args, github_api):
    repository_info = RepositoryInfo()
    repository_info.read_working_path(repo_path)
    push_action = PushAction(repository_info, push_args, github_api=github_api)
    push_action.execute()


def test_create(repo_path, tsrc_cli, github_mock, push_args):
    stub_repo = mock.Mock()
    stub_repo.iter_pulls.return_value = list()
    github_mock.repository.return_value = stub_repo
    stub_pr = mock.Mock()
    stub_repo.create_pull.return_value = stub_pr
    stub_pr.html_url = "https://github.com/foo/bar/pull/42"

    tsrc.git.run_git(repo_path, "checkout", "-b", "new-feature")
    tsrc.git.run_git(repo_path, "commit", "--message", "new feature", "--allow-empty")
    push_args.title = "new feature"
    execute_push(repo_path, push_args, github_mock)

    github_mock.repository.assert_called_with("foo", "bar")
    stub_repo.iter_pulls.assert_called_with()
    stub_repo.create_pull.assert_called_with("new feature", "master", "new-feature")


def test_merge(repo_path, tsrc_cli, github_mock, push_args):
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
    opened_pr_wrong_branch.state = "closed"
    opened_pr_wrong_branch.head.ref = "new-feature"

    stub_repo = mock.Mock()
    stub_repo.iter_pulls.return_value = [closed_pr, opened_pr, opened_pr_wrong_branch]
    github_mock.repository.return_value = stub_repo

    tsrc.git.run_git(repo_path, "checkout", "-b", "new-feature")
    tsrc.git.run_git(repo_path, "commit", "--message", "new feature", "--allow-empty")
    push_args.merge = True
    execute_push(repo_path, push_args, github_mock)

    stub_repo.create_pull.assert_not_called()
    opened_pr.merge.assert_called_with()
