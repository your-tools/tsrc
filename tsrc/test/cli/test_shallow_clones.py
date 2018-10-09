from path import Path

import tsrc
import tsrc.git

from ui.tests.conftest import message_recorder
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer


def assert_shallow_clone(workspace_path: Path, repo: str) -> None:
    repo_path = workspace_path / repo
    assert tsrc.git.is_shallow(repo_path)


def test_shallow_clones(tsrc_cli: CLI, git_server: GitServer, workspace_path: Path) -> None:
    git_server.add_repo("foo/bar")
    git_server.add_repo("spam/eggs")
    git_server.push_file("foo/bar", "bar.txt", contents="this is bar")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", "--shallow", manifest_url)
    assert_shallow_clone(workspace_path, "foo/bar")
    assert_shallow_clone(workspace_path, "spam/eggs")

    git_server.add_repo("foo/baz")
    tsrc_cli.run("sync")
    assert_shallow_clone(workspace_path, "foo/baz")


def test_shallow_with_fix_ref(tsrc_cli: CLI, git_server: GitServer,
                              workspace_path: Path, message_recorder: message_recorder) -> None:
    git_server.add_repo("foo")
    initial_sha1 = git_server.get_sha1("foo")
    git_server.push_file("foo", "one.c")
    git_server.manifest.set_repo_sha1("foo", initial_sha1)

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", "--shallow", manifest_url, expect_fail=True)
    assert message_recorder.find("Cannot use --shallow with a fixed sha1")
