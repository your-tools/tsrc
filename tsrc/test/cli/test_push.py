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

    def get_service(url: str) -> str:
        return tsrc.cli.push.service_from_url(url, workspace_mock)

    assert get_service("git@github.com:TankerHQ/tsrc.git") == "github"
    assert get_service("git@gitlab.ex.co:TankerHQ/tsrc.git") == "gitlab"
    assert get_service("git@github.ex.co:TankerHQ/tsrc.git") == "github_enterprise"
    assert get_service("git@git.ex.co:TankerHQ/tsrc.git") == "git"

    workspace_mock.get_github_enterprise_url.return_value = (
        "https://github.ex.co:8443/github"
    )
    workspace_mock.get_gitlab_url.return_value = "https://gitlab.ex.co:8443/gitlab"
    assert get_service("git@gitlab.ex.co:TankerHQ/tsrc.git") == "gitlab"
    assert get_service("git@github.ex.co:TankerHQ/tsrc.git") == "github_enterprise"
    assert get_service("git@gitlab.ex.co:8443:TankerHQ/tsrc.git") == "gitlab"
    assert get_service("git@github.ex.co:8443:TankerHQ/tsrc.git") == "github_enterprise"


def test_project_name_from_url() -> None:
    def project_name(url: str) -> str:
        return tsrc.cli.push.project_name_from_url(url)

    assert project_name("git@ex.co:foo/bar.git") == "foo/bar"
    assert project_name("ssh://git@ex.co:8022/foo/bar.git") == "foo/bar"


def mock_workspace_git_urls() -> mock.Mock:
    workspace_mock = mock.Mock(tsrc.Workspace)
    workspace_mock.get_github_enterprise_url.return_value = "https://github.ex.co/"
    workspace_mock.get_gitlab_url.return_value = "https://gitlab.ex.co/"

    return workspace_mock
