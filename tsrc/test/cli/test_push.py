import argparse
import mock

from path import Path
import tsrc
from tsrc.cli.push_git import PushAction


def test_push_use_tracked_branch(
    repo_path: Path, push_args: argparse.Namespace
) -> None:
    tsrc.git.run(repo_path, "checkout", "-b", "local")
    tsrc.git.run(repo_path, "push", "-u", "origin", "local:remote")

    repository_info = tsrc.cli.push.RepositoryInfo(mock_workspace_git_urls(), repo_path)
    dummy_push = PushAction(repository_info, push_args)
    dummy_push.push()
    _, out = tsrc.git.run_captured(repo_path, "ls-remote")
    assert "local" not in out
    assert "heads/remote" in out


def test_push_use_given_push_spec(
    repo_path: Path, push_args: argparse.Namespace
) -> None:
    tsrc.git.run(repo_path, "checkout", "-b", "local")
    push_args.push_spec = "local:remote"
    repository_info = tsrc.cli.push.RepositoryInfo(mock_workspace_git_urls(), repo_path)
    dummy_push = PushAction(repository_info, push_args)
    dummy_push.push()
    _, out = tsrc.git.run_captured(repo_path, "ls-remote")
    assert "local" not in out
    assert "heads/remote" in out


def test_service_from_url() -> None:
    workspace_mock = mock_workspace_git_urls()

    assert "github" == tsrc.cli.push.service_from_url("git@github.com:TankerHQ/tsrc.git", workspace_mock)
    assert "gitlab" == tsrc.cli.push.service_from_url("git@gitlab.example.com:TankerHQ/tsrc.git", workspace_mock)
    assert "github_enterprise" == tsrc.cli.push.service_from_url("git@github.example.com:TankerHQ/tsrc.git",
                                                                 workspace_mock)
    assert "git" == tsrc.cli.push.service_from_url("git@git.example.com:TankerHQ/tsrc.git", workspace_mock)

    workspace_mock.get_github_enterprise_url.return_value = "https://github.example.com:8443/github"
    workspace_mock.get_gitlab_url.return_value = "https://gitlab.example.com:8443/gitlab"
    assert "gitlab" == tsrc.cli.push.service_from_url("git@gitlab.example.com:TankerHQ/tsrc.git", workspace_mock)
    assert "github_enterprise" == tsrc.cli.push.service_from_url("git@github.example.com:TankerHQ/tsrc.git",
                                                                 workspace_mock)
    assert "gitlab" == tsrc.cli.push.service_from_url("git@gitlab.example.com:8443:TankerHQ/tsrc.git", workspace_mock)
    assert "github_enterprise" == tsrc.cli.push.service_from_url("git@github.example.com:8443:TankerHQ/tsrc.git",
                                                                 workspace_mock)


def test_project_name_from_url() -> None:
    assert "foo/bar" == tsrc.cli.push.project_name_from_url('git@example.com:foo/bar.git')
    assert "foo/bar" == tsrc.cli.push.project_name_from_url('ssh://git@example.com:8022/foo/bar.git')


def mock_workspace_git_urls() -> tsrc.Workspace:
    workspace_mock = mock.Mock()
    workspace_mock.get_github_enterprise_url.return_value = "https://github.example.com/"
    workspace_mock.get_gitlab_url.return_value = "https://gitlab.example.com/"

    return workspace_mock
