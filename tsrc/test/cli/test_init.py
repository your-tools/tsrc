from typing import cast, Any
from cli_ui.tests import MessageRecorder

import tsrc
import tsrc.git
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer

from path import Path


def repo_exists(workspace_path: Path, repo: str) -> bool:
    res = (workspace_path / repo).exists()
    return cast(bool, res)


def assert_cloned(workspace_path: Path, repo: str) -> None:
    assert repo_exists(workspace_path, repo)


def assert_not_cloned(workspace_path: Path, repo: str) -> None:
    assert not repo_exists(workspace_path, repo)


def test_init_simple(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    git_server.add_repo("foo/bar")
    git_server.add_repo("spam/eggs")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    assert_cloned(workspace_path, "foo/bar")
    assert_cloned(workspace_path, "spam/eggs")


def test_init_with_args(
    tsrc_cli: CLI, git_server: GitServer, monkeypatch: Any, tmp_path: Path
) -> None:
    git_server.add_repo("foo")
    work2_path = (tmp_path / "work2").mkdir()
    tsrc_cli.run("init", "--workspace", work2_path, git_server.manifest_url)
    assert_cloned(work2_path, "foo")


def test_cannot_init_twice(tsrc_cli: CLI, git_server: GitServer) -> None:
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    tsrc_cli.run("init", manifest_url, expect_fail=True)


def test_init_maint_manifest_branch(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    git_server.add_repo("bar")
    # foo repo will only exist on the 'devel' branch of the manifest:
    git_server.manifest.change_branch("devel")
    git_server.add_repo("foo")

    tsrc_cli.run("init", "--branch", "devel", git_server.manifest_url)

    assert_cloned(workspace_path, "foo")


def test_copy_files_happy(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    manifest_url = git_server.manifest_url
    git_server.add_repo("master")
    top_cmake_contents = "# Top CMakeLists.txt"
    git_server.push_file("master", "top.cmake", contents=top_cmake_contents)
    git_server.manifest.set_repo_file_copies(
        "master", [("top.cmake", "CMakeLists.txt")]
    )

    tsrc_cli.run("init", manifest_url)

    assert (workspace_path / "CMakeLists.txt").text() == top_cmake_contents


def test_copy_files_source_does_not_exist(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    manifest_url = git_server.manifest_url
    git_server.add_repo("master")
    git_server.manifest.set_repo_file_copies(
        "master", [("top.cmake", "CMakeLists.txt")]
    )

    tsrc_cli.run("init", manifest_url, expect_fail=True)
    assert message_recorder.find("Failed to perform the following copies")


def test_uses_correct_branch_for_repo(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    git_server.add_repo("foo")
    git_server.change_repo_branch("foo", "next")
    git_server.push_file("foo", "next.txt")
    git_server.manifest.set_repo_branch("foo", "next")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)

    foo_path = workspace_path / "foo"
    assert tsrc.git.get_current_branch(foo_path) == "next"


def test_empty_repo(tsrc_cli: CLI, git_server: GitServer, workspace_path: Path) -> None:
    git_server.add_repo("foo", empty=True)
    git_server.add_repo("bar")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url, expect_fail=True)


def test_resets_to_tag(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    git_server.add_repo("foo")
    git_server.tag("foo", "v1.0")
    git_server.push_file("foo", "2.txt", message="Working on v2")
    git_server.manifest.set_repo_tag("foo", "v1.0")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)

    foo_path = workspace_path / "foo"
    _, expected_ref = tsrc.git.run_captured(foo_path, "rev-parse", "v1.0")
    _, actual_ref = tsrc.git.run_captured(foo_path, "rev-parse", "HEAD")
    assert expected_ref == actual_ref


def test_resets_to_sha1(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    git_server.add_repo("foo")
    initial_sha1 = git_server.get_sha1("foo")
    git_server.manifest.set_repo_sha1("foo", initial_sha1)

    git_server.push_file("foo", "2.txt", message="Working on v2")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)

    foo_path = workspace_path / "foo"
    _, actual_ref = tsrc.git.run_captured(foo_path, "rev-parse", "HEAD")
    assert initial_sha1 == actual_ref


def test_use_default_group(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    git_server.add_group("default", ["a", "b"])
    git_server.add_repo("c")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)

    assert_cloned(workspace_path, "a")
    assert_not_cloned(workspace_path, "c")


def test_clone_all_repos(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    git_server.add_group("default", ["a", "b"])
    git_server.add_repo("orphan")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url, "--clone-all-repos")

    assert_cloned(workspace_path, "a")
    assert_cloned(workspace_path, "b")
    assert_cloned(workspace_path, "orphan")


def test_use_specific_groups(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    """ Scenario:
    * the manifest contains two groups, 'foo' and 'spam'
    * the manifest contains one repo 'other'
    * the 'other' repo is configured with a file copy

    * the user runs `init --group foo, spam`

    * we don't want 'other' to be cloned
    * we don't want the file copy to be attempted
    """
    git_server.add_group("foo", ["bar", "baz"])
    git_server.add_group("spam", ["eggs", "beacon"])
    git_server.add_repo("other")
    git_server.push_file("other", "THANKS")
    git_server.manifest.set_repo_file_copies("other", [("THANKS", "THANKS.copy")])

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url, "--groups", "foo", "spam")

    assert_cloned(workspace_path, "bar")
    assert_cloned(workspace_path, "eggs")
    assert_not_cloned(workspace_path, "other")


def test_no_remote_named_origin(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    git_server.add_repo("foo")

    tsrc_cli.run("init", git_server.manifest_url)
    foo_path = workspace_path / "foo"
    tsrc.git.run(foo_path, "remote", "rename", "origin", "upstream")

    tsrc_cli.run("sync")


def test_repo_default_branch_not_master(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    git_server.add_repo("foo", default_branch="devel")

    tsrc_cli.run("init", git_server.manifest_url)

    foo_path = workspace_path / "foo"
    assert tsrc.git.get_current_branch(foo_path) == "devel"


def test_several_remotes(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    foo_url = git_server.add_repo("foo")
    # fmt: off
    git_server.manifest.set_repo_remotes(
        "foo",
        [("origin", foo_url),
         ("upstream", "git@upstream.com")])
    # fmt: on

    tsrc_cli.run("init", git_server.manifest_url)

    foo_path = workspace_path / "foo"
    rc, output = tsrc.git.run_captured(
        foo_path, "remote", "get-url", "upstream", check=False
    )
    assert rc == 0, output
    assert output == "git@upstream.com"
