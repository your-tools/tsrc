from path import Path

import tsrc.cli

from ui.tests.conftest import message_recorder
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer


def test_status_happy(tsrc_cli: CLI, git_server: GitServer, workspace_path:
                      Path, message_recorder: message_recorder) -> None:
    git_server.add_repo("foo/bar")
    git_server.add_repo("spam/eggs")
    git_server.push_file("foo/bar", "CMakeLists.txt")
    git_server.push_file("spam/eggs", "CMakeLists.txt")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    tsrc.git.run(
        workspace_path / "spam/eggs",
        "checkout", "-b", "fish"
    )

    tsrc_cli.run("status")

    assert message_recorder.find(r"\* foo/bar   master")
    assert message_recorder.find(r"\* spam/eggs fish")


def test_status_dirty(tsrc_cli: CLI, git_server: GitServer,
                      workspace_path: Path, message_recorder: message_recorder) -> None:
    git_server.add_repo("foo/bar")
    git_server.push_file("foo/bar", "CMakeLists.txt")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    (workspace_path / "foo/bar/CMakeLists.txt").write_text("DIRTY FILE")

    tsrc_cli.run("status")

    assert message_recorder.find(r"\* foo/bar master \(dirty\)")


def test_status_not_on_any_branch(tsrc_cli: CLI, git_server: GitServer,
                                  workspace_path: Path, message_recorder: message_recorder) -> None:
    git_server.add_repo("foo/bar")
    git_server.add_repo("spam/eggs")
    git_server.push_file("foo/bar", "CMakeLists.txt")
    git_server.push_file("spam/eggs", "CMakeLists.txt")
    tsrc_cli.run("init", git_server.manifest_url)
    # corrupt the git
    eggs_path = workspace_path / "spam/eggs"
    tsrc.git.run(eggs_path, "checkout", "HEAD~1")

    tsrc_cli.run("status")

    assert message_recorder.find(r"\* foo/bar \s+ master")
    assert message_recorder.find(r"\* spam/eggs [a-f0-9]{7}")


def test_status_on_tag(tsrc_cli: CLI, git_server: GitServer,
                       workspace_path: Path, message_recorder: message_recorder) -> None:
    git_server.add_repo("foo/bar")
    git_server.add_repo("spam/eggs")
    git_server.push_file("foo/bar", "CMakeLists.txt")
    git_server.push_file("spam/eggs", "CMakeLists.txt")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    tsrc.git.run(
        workspace_path / "spam/eggs",
        "tag", "v1.0"
    )

    tsrc_cli.run("status")

    assert message_recorder.find(r"\* foo/bar   master")
    assert message_recorder.find(r"\* spam/eggs master on v1.0")
