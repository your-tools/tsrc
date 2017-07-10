import os

import pytest

import tsrc.cli

from tsrc.test.conftest import *


def test_sync_happy(tsrc_cli, git_server, workspace_path):
    git_server.add_repo("foo/bar")
    git_server.add_repo("spam/eggs")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    git_server.push_file("foo/bar", "bar.txt",
                         contents="this is bar")

    tsrc_cli.run("sync")

    bar_txt_path = workspace_path.joinpath("foo", "bar", "bar.txt")
    assert bar_txt_path.text() == "this is bar"


def test_sync_with_errors(tsrc_cli, git_server, workspace_path, messages):
    git_server.add_repo("foo/bar")
    git_server.add_repo("spam/eggs")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    git_server.push_file("foo/bar", "bar.txt",
                         contents="Bar is true")
    bar_src = workspace_path.joinpath("foo/bar")
    bar_src.joinpath("bar.txt").write_text("Bar is false")

    tsrc_cli.run("sync", expect_fail=True)

    assert messages.find("Sync failed")
    assert messages.find("\* foo/bar")


def test_sync_finds_root(tsrc_cli, git_server, workspace_path, monkeypatch):
    git_server.add_repo("foo/bar")
    tsrc_cli.run("init", git_server.manifest_url)
    monkeypatch.chdir(workspace_path.joinpath("foo/bar"))
    tsrc_cli.run("sync")


def test_new_repo_added_to_manifest(tsrc_cli, git_server, workspace_path):
    git_server.add_repo("foo/bar")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    git_server.add_repo("spam/eggs")

    tsrc_cli.run("sync")

    assert workspace_path.joinpath("spam/eggs").exists()


def test_switching_branches(tsrc_cli, git_server, workspace_path):
    # Init with manifest_url on master
    git_server.add_repo("foo")
    tsrc_cli.run("init", git_server.manifest_url)
    # Create a new repo, bar, but only on the 'devel'
    # branch of the manifest
    manifest_repo = git_server.manifest_repo
    tsrc.git.run_git(manifest_repo, "checkout", "-b", "devel")
    tsrc.git.run_git(manifest_repo, "push", "origin", "--no-verify",
                     "devel:devel")
    git_server.add_repo("bar")
    bar_path = workspace_path.joinpath("bar")

    # Sync on master branch: bar should not be cloned
    tsrc_cli.run("sync")
    assert not bar_path.exists()

    # Re-init with --branch=devel, bar should be cloned
    tsrc_cli.run("init", "--branch", "devel", git_server.manifest_url)
    tsrc_cli.run("sync")
    assert bar_path.exists()


def test_sync_not_on_master(tsrc_cli, git_server, workspace_path, messages):
    git_server.add_repo("foo")
    git_server.add_repo("bar")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    foo_path = workspace_path.joinpath("foo")
    tsrc.git.run_git(foo_path, "checkout", "-B", "devel")
    # push so that sync still works
    tsrc.git.run_git(foo_path, "push", "-u", "origin", "devel", "--no-verify")

    tsrc_cli.run("sync")

    assert messages.find("not on the correct branch")


def test_copies_are_up_to_date(tsrc_cli, git_server, workspace_path):
    manifest_url = git_server.manifest_url
    git_server.add_repo("foo")
    git_server.push_file("foo", "foo.txt", contents="v1")
    git_server.add_file_copy("foo/foo.txt", "top.txt")
    tsrc_cli.run("init", manifest_url)
    git_server.push_file("foo", "foo.txt", contents="v2")

    tsrc_cli.run("sync")

    assert workspace_path.joinpath("top.txt").text() == "v2"


def test_copies_are_readonly(tsrc_cli, git_server, workspace_path):
    manifest_url = git_server.manifest_url
    git_server.add_repo("foo")
    git_server.push_file("foo", "foo.txt", contents="v1")
    git_server.add_file_copy("foo/foo.txt", "top.txt")

    tsrc_cli.run("init", manifest_url)

    foo_txt = workspace_path.joinpath("top.txt")
    assert not os.access(foo_txt, os.W_OK)
