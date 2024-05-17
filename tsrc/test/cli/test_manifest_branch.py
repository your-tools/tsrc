"""
Test Manifest Branch

'tsrc manifest' can change branch using '--branch'
this does happen in "header" part.

There are some checks and various kind of reports
on different states. Here it should be checked
all such important features
"""

from pathlib import Path

# import pytest
from cli_ui.tests import MessageRecorder

from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer


def test_manifest_cmd_branch(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Scenario:
    * 1st: Create repository
    * 2nd: init Workspace
    * 3rd: check manifest branch
    * 4th: change manifest branch
    * 5th: check after change
    * 6th: change manifest branch back (to see if message report is corret)
    * 7th: check after change
    * 8th: change to wrong branch (non-existant)
    * 9th: change to already present branch (should not change)
    """

    # 1st: Create repository
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    manifest_url = git_server.manifest_url
    git_server.manifest.change_branch("devel")

    # 2nd: init Workspace
    tsrc_cli.run("init", "--branch", "devel", manifest_url)

    # 3rd: check manifest branch
    message_recorder.reset()
    tsrc_cli.run("manifest")
    assert message_recorder.find(r":: Manifest's branch: devel")

    # 4th: change manifest branch
    message_recorder.reset()
    tsrc_cli.run("manifest", "--branch", "master")
    assert message_recorder.find(
        r"=> Accepting Manifest's branch change from: devel ~~> master"
    )

    # 5th: check after change
    message_recorder.reset()
    tsrc_cli.run("manifest")
    assert message_recorder.find(
        r":: Manifest's branch will change from: devel ~~> master"
    )

    # 6th: change manifest branch back (to see if message report is corret)
    message_recorder.reset()
    tsrc_cli.run("manifest", "--branch", "devel")
    assert message_recorder.find(
        r"=> Reverting previous update, Manifest's branch will stays on: devel"
    )

    # 7th: check after change
    message_recorder.reset()
    tsrc_cli.run("manifest")
    assert message_recorder.find(r":: Manifest's branch: devel")

    # 8th: change to wrong branch (non-existant)
    message_recorder.reset()
    tsrc_cli.run("manifest", "--branch", "xxx")
    assert message_recorder.find(
        r"=> Such Manifest's branch: xxx was not found on remote, ignoring"
    ), "manifest branch change must be resistant against non-existant branch"
    assert message_recorder.find(
        r":: Manifest's branch: devel"
    ), "report that wrong value does not impact current state"

    # 9th: change to already present branch (should not change)
    message_recorder.reset()
    tsrc_cli.run("manifest", "--branch", "devel")
    assert message_recorder.find(
        r"=> No change to Manifest's branch, it will still stays on: devel"
    )
