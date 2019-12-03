import os
from typing import List
import pytest

from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer
from cli_ui.tests import MessageRecorder


def get_cmd_for_foreach_test(shell: bool = False) -> List[str]:
    """ We need a cmd that:
     * can fail if not called with the correct 'shell'
       argument
       (to check `foreach -c` option)
     * can fail if a directory does not exist
       (to check `foreach` error handling)
    """
    if os.name == "nt":
        if shell:
            cmd = ["dir"]
        else:
            cmd = ["cmd.exe", "/c", "dir"]
    else:
        if shell:
            cmd = ["cd"]
        else:
            cmd = ["ls"]
    return cmd


def test_foreach_no_args(tsrc_cli: CLI, git_server: GitServer) -> None:
    git_server.add_repo("foo")
    tsrc_cli.run("init", git_server.manifest_url)
    with pytest.raises(SystemExit):
        tsrc_cli.run("foreach")


def test_foreach_with_errors(
    tsrc_cli: CLI, git_server: GitServer, message_recorder: MessageRecorder
) -> None:
    git_server.add_repo("foo")
    git_server.add_repo("spam")
    git_server.push_file("foo", "foo/bar.txt", contents="this is bar")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    cmd = get_cmd_for_foreach_test(shell=False)
    cmd.append("foo")
    tsrc_cli.run("foreach", *cmd, expect_fail=True)
    assert message_recorder.find("Command failed")
    assert message_recorder.find(r"\* spam")


def test_foreach_happy(
    tsrc_cli: CLI, git_server: GitServer, message_recorder: MessageRecorder
) -> None:
    git_server.add_repo("foo")
    git_server.add_repo("spam")
    git_server.push_file("foo", "doc/index.html")
    git_server.push_file("spam", "doc/index.html")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    cmd = get_cmd_for_foreach_test(shell=False)
    cmd.append("doc")
    tsrc_cli.run("foreach", *cmd)
    assert message_recorder.find("`%s`" % " ".join(cmd))


def test_foreach_shell(
    tsrc_cli: CLI, git_server: GitServer, message_recorder: MessageRecorder
) -> None:
    git_server.add_repo("foo")
    git_server.add_repo("spam")
    git_server.push_file("foo", "doc/index.html")
    git_server.push_file("spam", "doc/index.html")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    cmd = get_cmd_for_foreach_test(shell=True)
    cmd.append("doc")
    tsrc_cli.run("foreach", "-c", " ".join(cmd))
    assert message_recorder.find("`%s`" % " ".join(cmd))


def test_foreach_with_explicit_groups(
    tsrc_cli: CLI, git_server: GitServer, message_recorder: MessageRecorder
) -> None:
    git_server.add_group("foo", ["bar", "baz"])
    git_server.add_group("spam", ["eggs", "beacon"])
    git_server.add_repo("other")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url, "--groups", "foo", "spam")

    cmd = get_cmd_for_foreach_test(shell=False)

    message_recorder.reset()
    tsrc_cli.run("foreach", "-g", "foo", *cmd)

    assert message_recorder.find("bar\n")
    assert message_recorder.find("baz\n")
    assert not message_recorder.find("eggs\n")
    assert not message_recorder.find("other\n")


def test_foreach_with_groups_from_config(
    tsrc_cli: CLI, git_server: GitServer, message_recorder: MessageRecorder
) -> None:
    git_server.add_group("foo", ["bar", "baz"])
    git_server.add_group("spam", ["eggs", "beacon"])
    git_server.add_repo("other")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url, "--groups", "foo", "spam")

    cmd = get_cmd_for_foreach_test(shell=False)

    message_recorder.reset()
    tsrc_cli.run("foreach", "--groups-from-config", *cmd)

    assert message_recorder.find("bar\n")
    assert message_recorder.find("baz\n")
    assert message_recorder.find("eggs\n")
    assert not message_recorder.find("other\n")


def test_foreach_error_when_using_missing_groups(
    tsrc_cli: CLI, git_server: GitServer, message_recorder: MessageRecorder
) -> None:
    git_server.add_group("foo", ["bar", "baz"])
    git_server.add_group("spam", ["eggs", "beacon"])

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url, "-g", "foo")

    cmd = get_cmd_for_foreach_test(shell=False)

    message_recorder.reset()
    tsrc_cli.run("foreach", "-g", "foo", "-g", "spam", *cmd, expect_fail=True)


def test_foreach_all_cloned_repos_by_default(
    tsrc_cli: CLI, git_server: GitServer, message_recorder: MessageRecorder
) -> None:
    git_server.add_group("foo", ["bar", "baz"])
    git_server.add_group("spam", ["eggs", "bacon"])
    git_server.add_repo("other")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url, "--groups", "foo", "spam")

    cmd = get_cmd_for_foreach_test(shell=False)

    message_recorder.reset()
    tsrc_cli.run("foreach", *cmd)

    assert message_recorder.find("bar\n")
    assert message_recorder.find("baz\n")
    assert message_recorder.find("eggs\n")
    assert message_recorder.find("bacon\n")
    assert not message_recorder.find("other\n")


def test_cannot_start_cmd(tsrc_cli: CLI, git_server: GitServer) -> None:
    git_server.add_repo("foo")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    tsrc_cli.run("foreach", "no-such", expect_fail=True)
