import argparse

from path import Path
import tsrc
from tsrc.cli.push_git import PushAction
from tsrc.cli.push import RepositoryInfo


def test_push_use_tracked_branch(
    repo_path: Path, push_args: argparse.Namespace
) -> None:
    tsrc.git.run(repo_path, "checkout", "-b", "local")
    tsrc.git.run(repo_path, "push", "-u", "origin", "local:remote")

    repository_info = RepositoryInfo.read(
        repo_path, workspace=mock_workspace_git_urls()
    )
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
    repository_info = RepositoryInfo.read(
        repo_path, workspace=mock_workspace_git_urls()
    )
    dummy_push = PushAction(repository_info, push_args)
    dummy_push.push()
    _, out = tsrc.git.run_captured(repo_path, "ls-remote")
    assert "local" not in out
    assert "heads/remote" in out


def get_service(url: str, manifest: tsrc.Manifest) -> Optional[str]:
    return service_from_url(url, manifest=manifest)


def test_service_from_url_with_empty_manifest() -> None:
    manifest = tsrc.Manifest()

    assert get_service("git@github.com:TankerHQ/tsrc.git", manifest) == "github"
    assert get_service("git@gitlab.ex.co:TankerHQ/tsrc.git", manifest) is None
    assert get_service("git@github.ex.co:TankerHQ/tsrc.git", manifest) is None
    assert get_service("git@git.ex.co:TankerHQ/tsrc.git", manifest) is None


def test_service_from_url_with_manifest_config() -> None:
    manifest = tsrc.Manifest()
    manifest.github_enterprise_url = "https://github.ex.co:8443/github"
    manifest.gitlab_url = "https://gitlab.ex.co:8443/gitlab"

    # fmt: off
    assert get_service("git@gitlab.ex.co:TankerHQ/tsrc.git", manifest) == "gitlab"
    assert get_service("git@github.ex.co:TankerHQ/tsrc.git", manifest) == "github_enterprise"
    assert get_service("git@gitlab.ex.co:8443:TankerHQ/tsrc.git", manifest) == "gitlab"
    assert get_service("git@github.ex.co:8443:TankerHQ/tsrc.git", manifest) == "github_enterprise"
    # fmt: on


def test_project_name_from_url() -> None:
    def project_name(url: str) -> str:
        return tsrc.cli.push.project_name_from_url(url)

    assert project_name("git@ex.co:foo/bar.git") == "foo/bar"
    assert project_name("ssh://git@ex.co:8022/foo/bar.git") == "foo/bar"
