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


def test_init_maint_manifest_branch(tsrc_cli, git_server, workspace_path):
    git_server.add_repo("bar")
    # foo repo will only exist on the 'devel' branch of the manifest:
    git_server.manifest.change_branch("devel")
    git_server.add_repo("foo")

    tsrc_cli.run("init", "--branch", "devel", git_server.manifest_url)

    assert workspace_path.joinpath("foo").exists()


def test_change_repo_url(tsrc_cli, git_server, workspace_path):
    git_server.add_repo("foo")
    tsrc_cli.run("init", git_server.manifest_url)
    new_url = "git@example.com/foo"
    git_server.manifest.set_repo_url("foo", new_url)
    tsrc_cli.run("init", git_server.manifest_url)
    foo_path = workspace_path.joinpath("foo")
    _, actual_url = tsrc.git.run_git(foo_path, "remote", "get-url", "origin", raises=False)
    assert actual_url == new_url


def test_copy_files(tsrc_cli, git_server, workspace_path):
    manifest_url = git_server.manifest_url
    git_server.add_repo("master")
    top_cmake_contents = "# Top CMakeLists.txt"
    git_server.push_file("master", "top.cmake", contents=top_cmake_contents)
    git_server.manifest.set_repo_file_copies("master", [["top.cmake", "CMakeLists.txt"]])

    tsrc_cli.run("init", manifest_url)

    assert workspace_path.joinpath("CMakeLists.txt").text() == top_cmake_contents


def test_uses_correct_branch_for_repo(tsrc_cli, git_server, workspace_path):
    git_server.add_repo("foo")
    git_server.change_repo_branch("foo", "next")
    git_server.push_file("foo", "next.txt")
    git_server.manifest.set_repo_branch("foo", "next")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)

    foo_path = workspace_path.joinpath("foo")
    assert tsrc.git.get_current_branch(foo_path) == "next"


def test_empty_repo(tsrc_cli, git_server, workspace_path):
    git_server.add_repo("foo", empty=True)
    git_server.add_repo("bar")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url, expect_fail=True)


def test_resets_to_fixed_ref(tsrc_cli, git_server, workspace_path):
    git_server.add_repo("foo")
    git_server.tag("foo", "v1.0")
    git_server.push_file("foo", "2.txt", message="Working on v2")
    git_server.manifest.set_repo_ref("foo", "v1.0")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)

    foo_path = workspace_path.joinpath("foo")
    expected_ref = tsrc.git.run_git(foo_path, "rev-parse", "v1.0", raises=False)
    actual_ref = tsrc.git.run_git(foo_path, "rev-parse", "HEAD", raises=False)
    assert expected_ref == actual_ref
