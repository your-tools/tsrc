import mock

import pytest

import tsrc.git
import tsrc.gitlab
import tsrc.manifest


def test_tsrc_cli_help(tsrc_cli):
    tsrc_cli.run("--help")


def test_tsrc_cli_bad_args(tsrc_cli):
    tsrc_cli.run("bad", expect_fail=True)


def read_remote_manifest(workspace_path, git_server):
    tsrc.git.run_git(workspace_path, "clone", git_server.manifest_url)
    manifest_yml = workspace_path.joinpath("manifest", "manifest.yml")
    assert manifest_yml.exists()
    manifest = tsrc.manifest.Manifest()
    manifest.load(manifest_yml.text())
    return manifest


def test_git_server_add_repo_can_clone(workspace_path, git_server):
    foobar_url = git_server.add_repo("foo/bar")
    tsrc.git.run_git(workspace_path, "clone", foobar_url)
    assert workspace_path.joinpath("bar").exists()


def test_git_server_can_add_copies(workspace_path, git_server):
    git_server.add_repo("foo")
    git_server.add_file_copy("foo/foo.txt", "top.txt")
    manifest = read_remote_manifest(workspace_path, git_server)
    assert manifest.copyfiles == [("foo/foo.txt", "top.txt")]


def test_can_configure_gitlab(tmp_path, git_server):
    test_url = "http://gitlab.example.org"
    git_server.configure_gitlab(url=test_url)
    manifest = read_remote_manifest(tmp_path, git_server)
    assert manifest.gitlab["url"] == test_url


def test_git_server_add_repo_updates_manifest(workspace_path, git_server):
    git_server.add_repo("foo/bar")
    git_server.add_repo("spam/eggs")
    manifest = read_remote_manifest(workspace_path, git_server)
    repos = manifest.repos
    assert len(repos) == 2
    for _, url in repos:
        rc, out = tsrc.git.run_git(workspace_path, "ls-remote", url,
                                   raises=False)
        assert rc == 0
        assert "refs/heads/master" in out


def test_git_server_change_manifest_branch(workspace_path, git_server):
    git_server.add_repo("foo")
    git_server.change_manifest_branch("devel")
    git_server.add_repo("bar")

    tsrc.git.run_git(workspace_path, "clone", git_server.manifest_url,
                     "--branch", "devel")
    manifest_yml = workspace_path.joinpath("manifest", "manifest.yml")
    manifest = tsrc.manifest.Manifest()
    manifest.load(manifest_yml.text())

    assert len(manifest.repos) == 2


def test_git_server_change_repo_branch(workspace_path, git_server):
    foo_url = git_server.add_repo("foo")
    git_server.change_repo_branch("foo", "devel")
    git_server.push_file("foo", "devel.txt", contents="this is devel\n")
    tsrc.git.run_git(workspace_path, "clone", foo_url, "--branch", "devel")
    foo_path = workspace_path.joinpath("foo")
    assert foo_path.joinpath("devel.txt").text() == "this is devel\n"


def test_git_server_tag(workspace_path, git_server):
    foo_url = git_server.add_repo("foo")
    git_server.tag("foo", "v0.1")
    rc, out = tsrc.git.run_git(workspace_path, "ls-remote", foo_url, raises=False)
    assert rc == 0
    assert "refs/tags/v0.1" in out
