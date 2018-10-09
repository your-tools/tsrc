from path import Path

import tsrc
import tsrc.git

from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer


def test_tsrc_cli_help(tsrc_cli: CLI) -> None:
    tsrc_cli.run("--help")


def test_tsrc_cli_bad_args(tsrc_cli: CLI) -> None:
    tsrc_cli.run("bad", expect_fail=True)


def read_remote_manifest(workspace_path: Path, git_server: GitServer) -> tsrc.Manifest:
    tsrc.git.run(workspace_path, "clone", git_server.manifest_url)
    manifest_yml = workspace_path / "manifest/manifest.yml"
    manifest = tsrc.manifest.load(manifest_yml)
    return manifest


def test_git_server_add_repo_can_clone(workspace_path: Path, git_server: GitServer) -> None:
    foobar_url = git_server.add_repo("foo/bar")
    tsrc.git.run(workspace_path, "clone", foobar_url)
    assert (workspace_path / "bar").exists()


def test_git_server_can_add_copies(workspace_path: Path, git_server: GitServer) -> None:
    git_server.add_repo("foo")
    git_server.manifest.set_repo_file_copies("foo", [("foo.txt", "top.txt")])
    manifest = read_remote_manifest(workspace_path, git_server)
    assert manifest.copyfiles == [("foo/foo.txt", "top.txt")]


def test_can_configure_gitlab(tmp_path: Path, git_server: GitServer) -> None:
    test_url = "http://gitlab.example.org"
    git_server.manifest.configure_gitlab(url=test_url)
    manifest = read_remote_manifest(tmp_path, git_server)
    assert manifest.gitlab
    assert manifest.gitlab["url"] == test_url


def test_git_server_add_repo_updates_manifest(workspace_path: Path, git_server: GitServer) -> None:
    git_server.add_repo("foo/bar")
    git_server.add_repo("spam/eggs")
    manifest = read_remote_manifest(workspace_path, git_server)
    repos = manifest.get_repos()
    assert len(repos) == 2
    for repo in repos:
        clone_url = repo.clone_url
        _, out = tsrc.git.run_captured(workspace_path, "ls-remote", clone_url)
        assert "refs/heads/master" in out


def test_git_server_change_manifest_branch(workspace_path: Path, git_server: GitServer) -> None:
    git_server.add_repo("foo")
    git_server.manifest.change_branch("devel")
    git_server.add_repo("bar")

    tsrc.git.run(
        workspace_path,
        "clone", git_server.manifest_url, "--branch", "devel"
    )
    manifest_yml = workspace_path / "manifest/manifest.yml"
    manifest = tsrc.manifest.load(manifest_yml)

    assert len(manifest.get_repos()) == 2


def test_git_server_change_repo_branch(workspace_path: Path, git_server: GitServer) -> None:
    foo_url = git_server.add_repo("foo")
    git_server.change_repo_branch("foo", "devel")
    git_server.push_file("foo", "devel.txt", contents="this is devel\n")
    tsrc.git.run(workspace_path, "clone", foo_url, "--branch", "devel")
    foo_path = workspace_path / "foo"
    assert (foo_path / "devel.txt").text() == "this is devel\n"


def test_git_server_tag(workspace_path: Path, git_server: GitServer) -> None:
    foo_url = git_server.add_repo("foo")
    git_server.tag("foo", "v0.1")
    _, out = tsrc.git.run_captured(workspace_path, "ls-remote", foo_url)
    assert "refs/tags/v0.1" in out


def test_git_server_default_branch_devel(workspace_path: Path, git_server: GitServer) -> None:
    foo_url = git_server.add_repo("foo", default_branch="devel")
    tsrc.git.run(workspace_path, "clone", foo_url)
    foo_path = workspace_path / "foo"
    cloned_branch = tsrc.git.get_current_branch(foo_path)
    assert cloned_branch == "devel"

    manifest = read_remote_manifest(workspace_path, git_server)
    foo_config = manifest.get_repo("foo")
    assert foo_config.branch == "devel"
