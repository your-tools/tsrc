import os

import pytest

import tsrc.cli

from tsrc.test.conftest import *


def test_status_happy(tsrc_cli, git_server, workspace_path, messages):
    git_server.add_repo("foo/bar")
    git_server.add_repo("spam/eggs")
    git_server.push_file("foo/bar", "CMakeLists.txt")
    git_server.push_file("spam/eggs", "CMakeLists.txt")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    tsrc.git.run_git(workspace_path.joinpath("spam", "eggs"), "checkout", "-b",
                     "fish")

    tsrc_cli.run("status")

    assert messages.find("\* foo/bar   master")
    assert messages.find("\* spam/eggs fish")


def test_status_dirty(tsrc_cli, git_server, workspace_path, messages):
    git_server.add_repo("foo/bar")
    git_server.push_file("foo/bar", "CMakeLists.txt")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    workspace_path.joinpath("foo", "bar", "CMakeLists.txt").write_text("DIRTY FILE")

    tsrc_cli.run("status")

    assert messages.find("\* foo/bar master \(dirty\)")


def test_status_error(tsrc_cli, git_server, workspace_path, messages):
    git_server.add_repo("foo/bar")
    git_server.add_repo("spam/eggs")
    git_server.push_file("foo/bar", "CMakeLists.txt")
    git_server.push_file("spam/eggs", "CMakeLists.txt")
    tsrc_cli.run("init", git_server.manifest_url)
    # corrupt the git
    workspace_path.joinpath("spam", "eggs", ".git", "HEAD").remove()

    tsrc_cli.run("status")

    assert messages.find("\* foo/bar master")
    assert messages.find("Errors when getting branch")
