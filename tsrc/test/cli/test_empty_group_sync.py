from pathlib import Path
from shutil import move

# import pytest
from cli_ui.tests import MessageRecorder

from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer


def test_empty_group_sync__case_a(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Reason:

    Verify case when updating to Manifest that does not have
    any Groups defined, while current configuration does
    Groups configured.
    By default, Groups should be updated unless
    '--no-update-config' is provided to 'sync'
    Also '--ignore-missing-groups' should ignore Groups
    regardles some Groups are provided
    """

    # 1st: Create bunch of repos
    git_server.add_repo("repo_1")
    git_server.push_file("repo_1", "my_file_in_repo_1.txt")
    git_server.add_repo("repo_2")
    git_server.push_file("repo_2", "my_file_in_repo_2.txt")
    git_server.add_repo("repo_3")
    git_server.push_file("repo_3", "my_file_in_repo_3.txt")
    git_server.add_repo("repo_4")
    git_server.push_file("repo_4", "my_file_in_repo_4.txt")
    git_server.add_repo("repo_5")
    git_server.push_file("repo_5", "my_file_in_repo_5.txt")

    # 2nd: add Manifest repo
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("dev")
    manifest_url = git_server.manifest_url

    tsrc_cli.run("init", manifest_url, "--branch", "dev")

    # 6th: clean tsrc configuration
    # rmtree(workspace_path / ".tsrc")
    move(workspace_path / ".tsrc", workspace_path / ".old_tsrc")

    # 3rd: add bunch of Groups
    git_server.manifest.change_branch("master")
    git_server.add_group("group_1", ["manifest", "repo_1"])
    git_server.add_group("group_3", ["manifest", "repo_3"])
    git_server.add_group("group_5", ["manifest", "repo_5"])

    # 4th: init Workspace with only selected Groups
    tsrc_cli.run(
        "init",
        manifest_url,
        "--branch",
        "master",
        "--groups",
        "group_1",
        "group_3",
        "group_5",
    )

    # 5th display status for just group 'group_3'
    #   we have to understand that DM does not have defined 'group_3'
    #   or any Groups for that matter,
    #   therefore there is no DM 'desc' to display in this case
    message_recorder.reset()
    tsrc_cli.run("status", "--groups", "group_3")
    assert message_recorder.find(r"\* manifest master ~~ MANIFEST")
    assert message_recorder.find(r"\* repo_3   master")
    assert message_recorder.find(r"")
    # these should not be in output
    assert not message_recorder.find(r"\* repo_1")
    assert not message_recorder.find(r"\* repo_5")

    # 6th swith to manifest branch 'dev'
    tsrc_cli.run("manifest", "--branch", "dev")

    # ================== from here it is different ==================
    # 7th A: 'sync' to new branch
    tsrc_cli.run("sync")

    # ==================     here changes ends     ==================

    # 8th: now there are no Groups, so 'status' should print all repos
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* manifest \[ master \]= master ~~ MANIFEST")
    assert message_recorder.find(r"\* repo_1   \[ master \]  master")
    assert message_recorder.find(r"\* repo_2   \[ master \]  master")
    assert message_recorder.find(r"\* repo_3   \[ master \]  master")
    assert message_recorder.find(r"\* repo_4   \[ master \]  master")
    assert message_recorder.find(r"\* repo_5   \[ master \]  master")


def test_empty_group_sync__case_b(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Reason:

    Verify case when updating to Manifest that does not have
    any Groups defined, while current configuration does
    Groups configured.
    By default, Groups should be updated unless
    '--no-update-config' is provided to 'sync'
    Also '--ignore-missing-groups' should ignore Groups
    regardles some Groups are provided
    """

    # 1st: Create bunch of repos
    git_server.add_repo("repo_1")
    git_server.push_file("repo_1", "my_file_in_repo_1.txt")
    git_server.add_repo("repo_2")
    git_server.push_file("repo_2", "my_file_in_repo_2.txt")
    git_server.add_repo("repo_3")
    git_server.push_file("repo_3", "my_file_in_repo_3.txt")
    git_server.add_repo("repo_4")
    git_server.push_file("repo_4", "my_file_in_repo_4.txt")
    git_server.add_repo("repo_5")
    git_server.push_file("repo_5", "my_file_in_repo_5.txt")

    # 2nd: add Manifest repo
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("dev")
    manifest_url = git_server.manifest_url

    tsrc_cli.run("init", manifest_url, "--branch", "dev")

    # 6th: clean tsrc configuration
    # rmtree(workspace_path / ".tsrc")
    move(workspace_path / ".tsrc", workspace_path / ".old_tsrc")

    # 3rd: add bunch of Groups
    git_server.manifest.change_branch("master")
    git_server.add_group("group_1", ["manifest", "repo_1"])
    git_server.add_group("group_3", ["manifest", "repo_3"])
    git_server.add_group("group_5", ["manifest", "repo_5"])

    # 4th: init Workspace with only selected Groups
    tsrc_cli.run(
        "init",
        manifest_url,
        "--branch",
        "master",
        "--groups",
        "group_1",
        "group_3",
        "group_5",
    )

    # 5th display status for just group 'group_3'
    #   we have to understand that DM does not have defined 'group_3'
    #   or any Groups for that matter,
    #   therefore there is no DM 'desc' to display in this case
    message_recorder.reset()
    tsrc_cli.run("status", "--groups", "group_3")
    assert message_recorder.find(r"\* manifest master ~~ MANIFEST")
    assert message_recorder.find(r"\* repo_3   master")
    assert message_recorder.find(r"")
    # these should not be in output
    assert not message_recorder.find(r"\* repo_1")
    assert not message_recorder.find(r"\* repo_5")

    # 6th swith to manifest branch 'dev'
    tsrc_cli.run("manifest", "--branch", "dev")

    # ================== from here it is different ==================

    # 7th B: 'sync' to new branch providing Groups that does not found
    tsrc_cli.run("sync", "--ignore-missing-groups", "--groups", "group_3")
    # ==================     here changes ends     ==================

    # 8th: now there are no Groups, so 'status' should print all repos
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* manifest \[ master \]= master ~~ MANIFEST")
    assert message_recorder.find(r"\* repo_1   \[ master \]  master")
    assert message_recorder.find(r"\* repo_2   \[ master \]  master")
    assert message_recorder.find(r"\* repo_3   \[ master \]  master")
    assert message_recorder.find(r"\* repo_4   \[ master \]  master")
    assert message_recorder.find(r"\* repo_5   \[ master \]  master")
