import os

import pytest
import ruamel

import tsrc.cli


def test_init(tsrc_cli, git_server, workspace_path):
    git_server.add_repo("foo/bar")
    git_server.add_repo("spam/eggs")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    assert workspace_path.joinpath("foo", "bar").exists()
    assert workspace_path.joinpath("spam", "eggs").exists()


def test_init_with_args(tsrc_cli, git_server, monkeypatch, tmp_path):
    git_server.add_repo("foo")
    work2_path = tmp_path.joinpath("work2").mkdir()
    tsrc_cli.run("init", "--workspace", work2_path, git_server.manifest_url)
    assert work2_path.joinpath("foo").isdir()


def test_init_twice(tsrc_cli, git_server):
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    tsrc_cli.run("init", manifest_url)


def test_init_maint_branch(tsrc_cli, git_server, workspace_path):
    manifest_repo = git_server.manifest_repo
    tsrc.git.run_git(manifest_repo, "checkout", "-b", "maint")
    # add_repo will be made on the 'maint' branch, which means
    # we should get no repo at all when trying to init with 'master'
    # branch
    git_server.add_repo("foo")
    tsrc.git.run_git(manifest_repo, "push", "origin", "--no-verify",
                     "maint:maint")

    tsrc_cli.run("init", "--branch", "maint", git_server.manifest_url)

    assert workspace_path.joinpath("foo").exists()


def test_change_remote(tsrc_cli, git_server, workspace_path):
    git_server.add_repo("foo")
    tsrc_cli.run("init", git_server.manifest_url)
    new_url = "git@example.com/foo"
    git_server.change_repo_url("foo", new_url)
    tsrc_cli.run("init", git_server.manifest_url)
    foo_path = workspace_path.joinpath("foo")
    _, actual_url = tsrc.git.run_git(foo_path, "remote", "get-url", "origin", raises=False)
    assert actual_url == new_url


def test_copy_files(tsrc_cli, git_server, workspace_path):
    manifest_url = git_server.manifest_url
    git_server.add_repo("master")
    top_cmake_contents = "# Top CMakeLists.txt"
    git_server.push_file("master", "top.cmake", contents=top_cmake_contents)
    git_server.add_file_copy("master/top.cmake", "CMakeLists.txt")

    tsrc_cli.run("init", manifest_url)

    assert workspace_path.joinpath("CMakeLists.txt").text() == top_cmake_contents
