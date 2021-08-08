import sys
from pathlib import Path

import pytest
from cli_ui.tests import MessageRecorder

from tsrc.git import run_git
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer


def test_foreach_no_args(tsrc_cli: CLI, git_server: GitServer) -> None:
    git_server.add_repo("foo")
    tsrc_cli.run("init", git_server.manifest_url)
    with pytest.raises(SystemExit):
        tsrc_cli.run("foreach")


def test_foreach_with_errors(
    tsrc_cli: CLI, git_server: GitServer, message_recorder: MessageRecorder
) -> None:
    """Scenario:
    * Create a repo 'foo'
    * Create a repo 'bar' containing 'stuff.txt'

    Check that tsrc foreach -- ls stuff.txt fails, and prints
    the failing repo in the list of error
    """
    git_server.add_repo("foo")
    git_server.add_repo("bar")
    git_server.push_file("bar", "stuff.txt", contents="some stuff")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    tsrc_cli.run_and_fail("foreach", "ls", "stuff.txt")
    assert message_recorder.find("Command failed")
    assert message_recorder.find(r"\bfoo\b")


def test_foreach_happy(
    tsrc_cli: CLI, git_server: GitServer, message_recorder: MessageRecorder
) -> None:
    """Scenario:
    * Create two repos
    * Check that `tsrc foreach ls` works
    * Check that the string `ls` is printed
    """
    git_server.add_repo("foo")
    git_server.add_repo("spam")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    tsrc_cli.run("foreach", "ls")
    assert message_recorder.find("`ls`")


def test_foreach_parallel(
    tsrc_cli: CLI, git_server: GitServer, message_recorder: MessageRecorder
) -> None:
    """Scenario:
    * Create two repos
    * Check that `tsrc foreach ls` works
    * Check that the string `ls` is printed
    """
    git_server.add_repo("foo")
    git_server.add_repo("spam")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    tsrc_cli.run("foreach", "-j", "auto", "ls")
    assert message_recorder.find("`ls`")


def test_foreach_shell(
    tsrc_cli: CLI, git_server: GitServer, message_recorder: MessageRecorder
) -> None:
    """Scenario
    * Create two repos containing README.rst and README.md
    * Check that `tsrc foreach -c 'ls README*'` works
    """
    git_server.add_repo("foo")
    git_server.add_repo("bar")
    git_server.push_file("foo", "README.html")
    git_server.push_file("bar", "README.rst")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)

    tsrc_cli.run("foreach", "-c", "ls README*")


def test_foreach_with_explicit_groups(
    tsrc_cli: CLI, git_server: GitServer, message_recorder: MessageRecorder
) -> None:
    """Scenario
    * Create a manifest containing:
       * a group named `foo` with repos `bar` and `baz`,
       * a group named `spam` with repos `eggs` and `beacon`
       * a repo named `other`, not part of any group
    * Initialize a workspace from this manifest, using the `foo`
      group
    * Check that `tsrc foreach ---group "foo" --ls README` works and
      runs ls only on `bar` and `baz`
    """
    git_server.add_group("foo", ["bar", "baz"])
    git_server.add_group("spam", ["eggs", "beacon"])
    git_server.add_repo("other")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url, "--groups", "foo", "spam")

    message_recorder.reset()
    tsrc_cli.run("foreach", "-g", "foo", "--", "ls")

    assert message_recorder.find(r"\bbar\b")
    assert message_recorder.find(r"\bbaz\b")
    assert not message_recorder.find(r"\beggs\b")
    assert not message_recorder.find(r"\bother\b")


def test_foreach_with_groups_from_config(
    tsrc_cli: CLI, git_server: GitServer, message_recorder: MessageRecorder
) -> None:
    """
    * Create a manifest containing:
       * a group named `foo` with repos `bar` and `baz`,
       * a group named `spam` with repos `eggs` and `beacon`
       * a repo named `other`, not part of any group
    * Initialize a workspace from this manifest, using the `foo`
      and `spam` groups
    * Check that `tsrc foreach ---group "foo" --ls README` works and
      runs `ls` only on everything but `other`
    """
    git_server.add_group("foo", ["bar", "baz"])
    git_server.add_group("spam", ["eggs", "beacon"])
    git_server.add_repo("other")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url, "--groups", "foo", "spam")

    message_recorder.reset()
    tsrc_cli.run("foreach", "ls")

    assert message_recorder.find(r"\bbar\b")
    assert message_recorder.find(r"\bbaz\b")
    assert message_recorder.find(r"\beggs\b")
    assert not message_recorder.find(r"\bother\b")


def test_foreach_error_when_using_missing_groups(
    tsrc_cli: CLI, git_server: GitServer, message_recorder: MessageRecorder
) -> None:
    """
    * Create a manifest containing:
       * a group named `foo` with repos `bar` and `baz`,
       * a group named `spam` with repos `eggs` and `beacon`
    * Initialize a workspace from this manifest, using the `foo` group
    * Check that `tsrc foreach ---groups foo spam --ls` fails
    """
    git_server.add_group("foo", ["bar", "baz"])
    git_server.add_group("spam", ["eggs", "beacon"])

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url, "--group", "foo")

    message_recorder.reset()
    tsrc_cli.run_and_fail("foreach", "--groups", "foo", "spam", "--", "ls")


def test_foreach_with_all_cloned_repos_requested(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    * Create a manifest containing:
       * a group named `foo` with repos `bar` and `baz`,
       * a group named `spam` with repos `eggs` and `beacon`
       * a repo named `quux`, not part of any group
    * Initialize a workspace from this manifest, using the `foo` group
    * Force the clone of the `other` repo
    * Check that `tsrc foreach --all-cloned` visits all repos
    """
    git_server.add_group("foo", ["bar", "baz"])
    git_server.add_group("spam", ["eggs", "bacon"])
    quux_url = git_server.add_repo("quux")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url, "--groups", "foo", "spam")

    run_git(workspace_path, "clone", quux_url)
    message_recorder.reset()

    tsrc_cli.run("foreach", "--all-cloned", "ls")

    assert message_recorder.find(r"\bbar\b")
    assert message_recorder.find(r"\bbaz\b")
    assert message_recorder.find(r"\beggs\b")
    assert message_recorder.find(r"\bbacon\b")
    assert message_recorder.find(r"\bquux\b")


def test_cannot_start_cmd(tsrc_cli: CLI, git_server: GitServer) -> None:
    git_server.add_repo("foo")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    tsrc_cli.run_and_fail("foreach", "no-such")


def test_set_environment_variables(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    git_server.add_repo("foo")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)

    check_env_py = workspace_path / "check-env.py"
    check_env_py.write_text("import os; print(os.environ['TSRC_PROJECT_DEST'])")

    tsrc_cli.run("foreach", sys.executable, str(check_env_py))
