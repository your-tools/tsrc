import os

import pytest

import tsrc.cli

from tsrc.test.conftest import *


def get_cmd_for_foreach_test(shell=False):
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


def test_foreach_no_args(tsrc_cli, git_server):
    git_server.add_repo("foo")
    tsrc_cli.run("init", git_server.manifest_url)
    tsrc_cli.run("foreach", expect_fail=True)


def test_foreach_with_errors(tsrc_cli, git_server, messages):
    git_server.add_repo("foo")
    git_server.add_repo("spam")
    git_server.push_file("foo", "foo/bar.txt",
                         contents="this is bar")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    cmd = get_cmd_for_foreach_test(shell=False)
    cmd.append("foo")
    tsrc_cli.run("foreach", *cmd, expect_fail=True)
    assert messages.find("foreach failed")
    assert messages.find("\* spam")


def test_foreach_happy(tsrc_cli, git_server, messages):
    git_server.add_repo("foo")
    git_server.add_repo("spam")
    git_server.push_file("foo", "doc/index.html")
    git_server.push_file("spam", "doc/index.html")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    cmd = get_cmd_for_foreach_test(shell=False)
    cmd.append("doc")
    tsrc_cli.run("foreach", *cmd)
    assert messages.find("Running `%s` on foo" % " ".join(cmd))
    assert messages.find("Running `%s` on spam" % " ".join(cmd))


def test_foreach_shell(tsrc_cli, git_server, messages):
    git_server.add_repo("foo")
    git_server.add_repo("spam")
    git_server.push_file("foo", "doc/index.html")
    git_server.push_file("spam", "doc/index.html")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    cmd = get_cmd_for_foreach_test(shell=True)
    cmd.append("doc")
    tsrc_cli.run("foreach", "-c", " ".join(cmd))
    assert messages.find("Running `%s` on foo" % " ".join(cmd))
