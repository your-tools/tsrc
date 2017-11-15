import os

import pytest

import tsrc.cli

from tsrc.test.conftest import *


def test_sync_happy(tsrc_cli, git_server, workspace_path):
    git_server.add_repo("foo/bar")
    git_server.add_repo("spam/eggs")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    git_server.push_file("foo/bar", "bar.txt", contents="this is bar")

    tsrc_cli.run("sync")

    bar_txt_path = workspace_path.joinpath("foo", "bar", "bar.txt")
    assert bar_txt_path.text() == "this is bar"


def test_sync_with_errors(tsrc_cli, git_server, workspace_path, message_recorder):
    git_server.add_repo("foo/bar")
    git_server.add_repo("spam/eggs")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    git_server.push_file("foo/bar", "bar.txt", contents="Bar is true")
    bar_src = workspace_path.joinpath("foo/bar")
    bar_src.joinpath("bar.txt").write_text("Bar is false")

    tsrc_cli.run("sync", expect_fail=True)

    assert message_recorder.find("Synchronize workspace failed")
    assert message_recorder.find("\* foo/bar")


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


def test_switching_manifest_branches(tsrc_cli, git_server, workspace_path):
    # Init with manifest_url on master
    git_server.add_repo("foo")
    tsrc_cli.run("init", git_server.manifest_url)

    # Create a new repo, bar, but only on the 'devel'
    # branch of the manifest
    git_server.manifest.change_branch("devel")
    git_server.add_repo("bar")
    bar_path = workspace_path.joinpath("bar")

    # Sync on master branch: bar should not be cloned
    tsrc_cli.run("sync")
    assert not bar_path.exists()

    # Re-init with --branch=devel, bar should be cloned
    tsrc_cli.run("init", "--branch", "devel", git_server.manifest_url)
    tsrc_cli.run("sync")
    assert bar_path.exists()


def test_sync_not_on_master(tsrc_cli, git_server, workspace_path, message_recorder):
    git_server.add_repo("foo")
    git_server.add_repo("bar")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    foo_path = workspace_path.joinpath("foo")
    tsrc.git.run_git(foo_path, "checkout", "-B", "devel")
    # push so that sync still works
    tsrc.git.run_git(foo_path, "push", "-u", "origin", "devel", "--no-verify")

    tsrc_cli.run("sync", expect_fail=True)

    assert message_recorder.find("not on the correct branch")


def test_copies_are_up_to_date(tsrc_cli, git_server, workspace_path):
    manifest_url = git_server.manifest_url
    git_server.add_repo("foo")
    git_server.push_file("foo", "foo.txt", contents="v1")
    git_server.manifest.set_repo_file_copies("foo", [["foo.txt", "top.txt"]])
    tsrc_cli.run("init", manifest_url)
    git_server.push_file("foo", "foo.txt", contents="v2")

    tsrc_cli.run("sync")

    assert workspace_path.joinpath("top.txt").text() == "v2"


def test_copies_are_readonly(tsrc_cli, git_server, workspace_path):
    manifest_url = git_server.manifest_url
    git_server.add_repo("foo")
    git_server.push_file("foo", "foo.txt", contents="v1")
    git_server.manifest.set_repo_file_copies("foo", [["foo.txt", "top.txt"]])

    tsrc_cli.run("init", manifest_url)

    foo_txt = workspace_path.joinpath("top.txt")
    assert not os.access(foo_txt, os.W_OK)


def test_changing_branch(tsrc_cli, git_server, workspace_path, message_recorder):
    git_server.add_repo("foo")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)

    git_server.change_repo_branch("foo", "next")
    git_server.push_file("foo", "next.txt")
    git_server.manifest.set_repo_branch("foo", "next")

    tsrc_cli.run("sync", expect_fail=True)
    assert message_recorder.find("not on the correct branch")


def test_tags_are_not_updated(tsrc_cli, git_server, workspace_path):
    git_server.add_repo("foo")
    git_server.tag("foo", "v0.1")
    git_server.manifest.set_repo_tag("foo", "v0.1")

    tsrc_cli.run("init", git_server.manifest_url)

    git_server.push_file("foo", "new.txt")

    tsrc_cli.run("sync")

    foo_path = workspace_path.joinpath("foo")
    assert not foo_path.joinpath("new.txt").exists()


def test_sha1s_are_not_updated(tsrc_cli, git_server, workspace_path):
    git_server.add_repo("foo")
    initial_sha1 = git_server.get_sha1("foo")
    git_server.manifest.set_repo_sha1("foo", initial_sha1)

    tsrc_cli.run("init", git_server.manifest_url)

    git_server.push_file("foo", "new.txt")

    tsrc_cli.run("sync")

    foo_path = workspace_path.joinpath("foo")
    assert not foo_path.joinpath("new.txt").exists()


def test_tags_are_updated_when_clean(tsrc_cli, git_server, workspace_path):

    git_server.add_repo("foo")
    git_server.tag("foo", "v0.1")
    git_server.manifest.set_repo_tag("foo", "v0.1")

    tsrc_cli.run("init", git_server.manifest_url)

    git_server.push_file("foo", "new.txt")
    git_server.tag("foo", "v0.2")
    git_server.manifest.set_repo_tag("foo", "v0.2")

    tsrc_cli.run("sync")

    foo_path = workspace_path.joinpath("foo")
    assert foo_path.joinpath("new.txt").exists()


def test_sha1s_are_updated_when_clean(tsrc_cli, git_server, workspace_path):
    git_server.add_repo("foo")
    initial_sha1 = git_server.get_sha1("foo")
    git_server.manifest.set_repo_sha1("foo", initial_sha1)

    tsrc_cli.run("init", git_server.manifest_url)

    git_server.push_file("foo", "new.txt")
    new_sha1 = git_server.get_sha1("foo")
    git_server.manifest.set_repo_sha1("foo", new_sha1)

    tsrc_cli.run("sync")

    foo_path = workspace_path.joinpath("foo")
    assert foo_path.joinpath("new.txt").exists()


def test_tags_are_skipped_when_not_clean(tsrc_cli, git_server, workspace_path):
    git_server.add_repo("foo")
    git_server.tag("foo", "v0.1")
    git_server.manifest.set_repo_tag("foo", "v0.1")

    tsrc_cli.run("init", git_server.manifest_url)
    workspace_path.joinpath("foo", "untracked.txt").write_text("")

    git_server.push_file("foo", "new.txt")
    git_server.tag("foo", "v0.2")
    git_server.manifest.set_repo_tag("foo", "v0.2")

    tsrc_cli.run("sync", expect_fail=True)

    foo_path = workspace_path.joinpath("foo")
    assert not foo_path.joinpath("new.txt").exists()


def test_tags_are_skipped_when_not_clean(tsrc_cli, git_server, workspace_path):
    git_server.add_repo("foo")
    initial_sha1 = git_server.get_sha1("foo")
    git_server.manifest.set_repo_sha1("foo", initial_sha1)

    tsrc_cli.run("init", git_server.manifest_url)
    workspace_path.joinpath("foo", "untracked.txt").write_text("")

    git_server.push_file("foo", "new.txt")
    new_sha1 = git_server.get_sha1("foo")
    git_server.manifest.set_repo_sha1("foo", new_sha1)

    tsrc_cli.run("sync", expect_fail=True)

    foo_path = workspace_path.joinpath("foo")
    assert not foo_path.joinpath("new.txt").exists()


def test_custom_group(tsrc_cli, git_server, message_recorder):
    git_server.add_group("foo", ["bar", "baz"])
    git_server.add_repo("other")

    tsrc_cli.run("init", git_server.manifest_url, "--group", "foo")

    message_recorder.reset()
    tsrc_cli.run("sync")
    assert message_recorder.find("bar")
    assert not message_recorder.find("other")
