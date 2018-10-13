import os

import mock
from path import Path

from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer
from ui.tests.conftest import message_recorder


def get_cat_cmd() ->str:
    # We need a command that:
    #    * Always exists, both on Windows and Unix
    #    * can fail if a file does not exist (to check `foreach` error handling)
    if os.name == "nt":
        return "type"
    else:
        return "cat"


def test_foreach_no_args(tsrc_cli: CLI, git_server: GitServer) -> None:
    git_server.add_repo("foo")
    tsrc_cli.run("init", git_server.manifest_url)
    tsrc_cli.run("foreach", expect_fail=True)


def test_foreach_with_errors(
        tsrc_cli: CLI, git_server: GitServer,
        message_recorder: message_recorder) -> None:
    git_server.add_repo("foo")
    git_server.add_repo("spam")
    git_server.push_file("foo", "bar.txt",
                         contents="this is bar")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    cmd = [get_cat_cmd(), "bar.txt"]
    tsrc_cli.run("foreach", *cmd, expect_fail=True)
    assert message_recorder.find("Command failed")
    assert message_recorder.find(r"\* spam")


def test_foreach_happy(
        tsrc_cli: CLI, git_server: GitServer,
        message_recorder: message_recorder) -> None:
    git_server.add_repo("foo")
    git_server.add_repo("spam")
    git_server.push_file("foo", "index.html")
    git_server.push_file("spam", "index.html")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    cmd = [get_cat_cmd(), "index.html"]
    tsrc_cli.run("foreach", *cmd)
    assert message_recorder.find("`%s`" % " ".join(cmd))


def test_foreach_shell(
        tsrc_cli: CLI, git_server: GitServer, workspace_path: Path,
        message_recorder: message_recorder) -> None:
    git_server.add_repo("foo")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    foo_path = workspace_path / "foo"
    with mock.patch("subprocess.call") as subprocess_mock:
        subprocess_mock.return_value = 0
        tsrc_cli.run("foreach", "-c", "command")
        calls = subprocess_mock.call_args_list
        first_call = calls[0]
        args, kwargs = first_call
        assert args[0] == "command"
        assert kwargs["shell"]
        assert kwargs["cwd"] == foo_path


def test_foreach_groups_happy(
        tsrc_cli: CLI, git_server: GitServer,
        message_recorder: message_recorder) -> None:
    git_server.add_group("foo", ["bar", "baz"])
    git_server.add_group("spam", ["eggs", "beacon"])
    git_server.add_repo("other")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url, "-g", "foo", "-g", "spam")

    cmd = [get_cat_cmd(), "README"]

    message_recorder.reset()
    tsrc_cli.run("foreach", "-g", "foo", *cmd)

    assert message_recorder.find("bar\n")
    assert message_recorder.find("baz\n")
    assert not message_recorder.find("eggs\n")
    assert not message_recorder.find("other\n")


def test_foreach_groups_warn_skipped(
        tsrc_cli: CLI, git_server: GitServer,
        message_recorder: message_recorder) -> None:
    git_server.add_group("foo", ["bar", "baz"])
    git_server.add_group("spam", ["eggs", "beacon"])
    git_server.add_repo("other")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url, "-g", "foo")

    cmd = [get_cat_cmd(), "README"]

    message_recorder.reset()
    tsrc_cli.run("foreach", "-g", "foo", "-g", "spam", *cmd)
