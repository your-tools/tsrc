import os
from pathlib import Path
from typing import Any

from cli_ui.tests import MessageRecorder

from tsrc.git import get_current_branch, run_git, run_git_captured
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer
from tsrc.workspace import ClonerError


def repo_exists(workspace_path: Path, repo: str) -> bool:
    return (workspace_path / repo).exists()


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
    work2_path = tmp_path / "work2"
    work2_path.mkdir()
    tsrc_cli.run("init", "--workspace", str(work2_path), git_server.manifest_url)
    assert_cloned(work2_path, "foo")


def test_cannot_init_twice(tsrc_cli: CLI, git_server: GitServer) -> None:
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    tsrc_cli.run_and_fail("init", manifest_url)


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
    """Scenario:
    * Crate a manifest with a 'top' repo
    * Configure the 'top' repo with a file copy from 'top.cmake' to 'CMakeLists.txt'
    * Push `top.cmake` to the `top` repo
    * Run `tsrc init`
    * Check that a `CMakeLists.txt` file was created at the root of the
      workspace
    """
    manifest_url = git_server.manifest_url
    git_server.add_repo("top")
    top_cmake_contents = "# Top CMakeLists.txt"
    git_server.push_file("top", "top.cmake", contents=top_cmake_contents)
    git_server.manifest.set_file_copy("top", "top.cmake", "CMakeLists.txt")

    tsrc_cli.run("init", manifest_url)

    assert (workspace_path / "CMakeLists.txt").read_text() == top_cmake_contents


def test_copy_files_source_does_not_exist(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """Scenario:
    * Crate a manifest with a 'top' repo
    * Configure the 'top' repo with a file copy from 'top.cmake' to 'CMakeLists.txt'
    * Check that `tsrc init` fails (the `top.cmake` file is missing from the
      'top' repo)
    """
    manifest_url = git_server.manifest_url
    git_server.add_repo("top")
    git_server.manifest.set_file_copy("top", "top.cmake", "CMakeLists.txt")

    tsrc_cli.run_and_fail("init", manifest_url)
    assert message_recorder.find("Failed to perform")


def test_clone_destination_is_a_file(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    manifest_url = git_server.manifest_url
    git_server.add_repo("foo")

    with (workspace_path / "foo").open("w") as f:
        f.write("this is a file")

    tsrc_cli.run_and_fail_with(ClonerError, "init", manifest_url)


def test_create_symlink(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    """Scenario:
    * Crate a manifest with a 'foo' repo
    * Push 'foo.txt' to the 'foo' repo
    * Configure the 'foo' repo with a symlink copy from 'foo.link' to 'foo/foo.txt'
    * Run `tsrc init`
    * Check that a link exists in <workspace>/foo.link pointing to foo/foo.txt
    """
    manifest_url = git_server.manifest_url
    git_server.add_repo("foo")
    git_server.push_file("foo", "foo.txt")
    git_server.manifest.set_symlink("foo", "foo.link", "foo/foo.txt")

    tsrc_cli.run("init", manifest_url)

    actual_link = workspace_path / "foo.link"
    assert actual_link.exists()
    assert os.readlink(str(actual_link)) == os.path.normpath("foo/foo.txt")


def test_uses_correct_branch_for_repo(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    """Scenario:
    * Create a foo repo with two branches `master` and `next`
    * Set the branch to `next` in the manifest
    * Init the repository
    * Check that the cloned project is on the `next` branch

    """
    git_server.add_repo("foo")
    git_server.push_file("foo", "next.txt", branch="next")
    git_server.manifest.set_repo_branch("foo", "next")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)

    foo_path = workspace_path / "foo"
    assert get_current_branch(foo_path) == "next"


def test_empty_repo(tsrc_cli: CLI, git_server: GitServer, workspace_path: Path) -> None:
    """Scenario:
    * Create a manifest containing an empty repo
    * Check that `tsrc init` fails but does not crash
    """
    git_server.add_repo("foo", empty=True)
    git_server.add_repo("bar")

    manifest_url = git_server.manifest_url

    tsrc_cli.run_and_fail("init", manifest_url)


def test_resets_to_tag(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    """Scenario:
    * Create a repository containing a v1.0 tag
    * Add a commit on top of the v1.0 tag
    * Configure the manifest to specify that the repo
      should be reset at the v1.0 tag
    * Run `tsrc init`
    * Check the repo was cloned at the correct revision
    """
    git_server.add_repo("foo")
    git_server.tag("foo", "v1.0")
    git_server.push_file("foo", "2.txt", message="Working on v2")
    git_server.manifest.set_repo_tag("foo", "v1.0")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)

    foo_path = workspace_path / "foo"
    _, expected_ref = run_git_captured(foo_path, "rev-parse", "v1.0")
    _, actual_ref = run_git_captured(foo_path, "rev-parse", "HEAD")
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
    _, actual_ref = run_git_captured(foo_path, "rev-parse", "HEAD")
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
    """Scenario:
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
    git_server.manifest.set_file_copy("other", "THANKS", "THANKS.copy")

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
    run_git(foo_path, "remote", "rename", "origin", "upstream")

    tsrc_cli.run("sync")


def test_repo_default_branch_not_master(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    git_server.add_repo("foo", default_branch="devel")

    tsrc_cli.run("init", git_server.manifest_url)

    foo_path = workspace_path / "foo"
    assert get_current_branch(foo_path) == "devel"


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
    rc, output = run_git_captured(
        foo_path, "remote", "get-url", "upstream", check=False
    )
    assert rc == 0, output
    assert output == "git@upstream.com"


def test_singular_remote(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    """
    Scenario:
     * Create a manifest that contains one repo with two remotes
       ('origin' and 'vpn')
     * Make sure that the `origin` URL is valid but the `vpn`
       URL is not.
     * Run `tsrc init --remote origin`
     * Check that foo only has one remote called 'origin'
    """
    foo_url = git_server.add_repo("foo")
    vpn_url = "/does/not/exist"
    # fmt: off
    git_server.manifest.set_repo_remotes(
        "foo",
        [("origin", foo_url),
         ("vpn", vpn_url)])
    # fmt: on

    # only use "origin" remote
    tsrc_cli.run("init", git_server.manifest_url, "-r", "origin")

    foo_path = workspace_path / "foo"
    _, output = run_git_captured(foo_path, "remote", "show", check=True)

    assert output == "origin"


def test_clone_submodules(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    """
    Scenario:
    * Create repo 'sub1' containing a 'sub2' submodule
    * Create a repo 'top' containing the 'sub1' submodule
    * Add 'top' to the manifest
    * Run `tsrc init`
    * Check that both submodules where cloned properly
    """

    git_server.add_repo("top")
    sub1_url = git_server.add_repo("sub1", add_to_manifest=False)
    sub2_url = git_server.add_repo("sub2", add_to_manifest=False)
    git_server.add_submodule("sub1", url=sub2_url, path=Path("sub2"))
    git_server.add_submodule("top", url=sub1_url, path=Path("sub1"))

    tsrc_cli.run("init", git_server.manifest_url, "-r", "origin")

    clone_path = workspace_path / "top"

    sub1_readme = clone_path / "sub1" / "README"
    assert sub1_readme.exists(), "sub1 was not cloned"

    sub2_readme = clone_path / "sub1" / "sub2" / "README"
    assert sub2_readme.exists(), "sub2 was not cloned"
