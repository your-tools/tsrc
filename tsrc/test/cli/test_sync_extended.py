from pathlib import Path
from shutil import move

# import pytest
from cli_ui.tests import MessageRecorder

from tsrc.git import run_git
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer


def test_sync_on_groups_intersection__case_1(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Reason:

    when new Manifest (on different branch) does
    have different Groups defined, we may want
    to update them to config.
    If we do not do it, we can end up with error
    even for default listing.
    (only when 'clone_all_repos'=false)

    This is not desired and by default when
    no Groups are provided for 'tsrc sync',
    new Groups should be updated to config.

    We can still disable this behavior by providing:
    '--no-update-config' for 'tsrc sync' command

    And here we should test both cases if they
    work as declared.

    Cases:

    * 1st: plain sync
    * 2nd: sync with 'no-update-config'
    * 3rd: A: sync with 'ignore-missing-group'
    * 3rd: B: sync with 'ignore-missing-group', while provide 'groups'
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
    git_server.manifest.change_branch("master")
    manifest_url = git_server.manifest_url

    # 3rd: add bunch of Groups
    git_server.add_group("group_1", ["manifest", "repo_1"])
    git_server.add_group("group_3", ["manifest", "repo_3"])
    git_server.add_group("group_5", ["manifest", "repo_5"])

    # 4th: init Workspace with only selected Groups
    tsrc_cli.run("init", manifest_url, "--groups", "group_1", "group_3", "group_5")

    # 5th: save and push current Manifest to different Git Branch (dev)
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-B", "dev")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # 6th: clean tsrc configuration
    # rmtree(workspace_path / ".tsrc")
    move(workspace_path / ".tsrc", workspace_path / ".old_tsrc")

    # 7th: init workspace with only selected group
    tsrc_cli.run("init", "--branch", "master", manifest_url, "--groups", "group_3")

    # 8th: change Manifest branch for next sync to 'dev'
    tsrc_cli.run("manifest", "--branch", "dev")

    # ================== from here it is different ==================
    # 9th: sync (use specific case for given test)
    # case: 1
    tsrc_cli.run("sync")

    # 10th: very by 'status' output
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* manifest \[ master \]= master ~~ MANIFEST")
    assert message_recorder.find(r"\* repo_1   \[ master \]  master")
    assert message_recorder.find(r"\* repo_3   \[ master \]  master")
    assert message_recorder.find(r"\* repo_5   \[ master \]  master")


def test_sync_on_groups_intersection__case_2(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Reason:

    when new Manifest (on different branch) does
    have different Groups defined, we may want
    to update them to config.
    If we do not do it, we can end up with error
    even for default listing.
    (only when 'clone_all_repos'=false)

    This is not desired and by default when
    no Groups are provided for 'tsrc sync',
    new Groups should be updated to config.

    We can still disable this behavior by providing:
    '--no-update-config' for 'tsrc sync' command

    And here we should test both cases if they
    work as declared.

    Cases:

    * 1st: plain sync
    * 2nd: sync with 'no-update-config'
    * 3rd: A: sync with 'ignore-missing-group'
    * 3rd: B: sync with 'ignore-missing-group', while provide 'groups'
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
    git_server.manifest.change_branch("master")
    manifest_url = git_server.manifest_url

    # 3rd: add bunch of Groups
    git_server.add_group("group_1", ["manifest", "repo_1"])
    git_server.add_group("group_3", ["manifest", "repo_3"])
    git_server.add_group("group_5", ["manifest", "repo_5"])

    # 4th: init Workspace with only selected Groups
    tsrc_cli.run("init", manifest_url, "--groups", "group_1", "group_3", "group_5")

    # 5th: save and push current Manifest to different Git Branch (dev)
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-B", "dev")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # 6th: clean tsrc configuration
    # rmtree(workspace_path / ".tsrc")
    move(workspace_path / ".tsrc", workspace_path / ".old_tsrc")

    # 7th: init workspace with only selected group
    tsrc_cli.run("init", "--branch", "master", manifest_url, "--groups", "group_3")

    # 8th: change Manifest branch for next sync to 'dev'
    tsrc_cli.run("manifest", "--branch", "dev")

    # ================== from here it is different ==================
    # 9th: case: 2
    tsrc_cli.run("sync", "--no-update-config")

    # 10th: very by 'status' output
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* manifest \[ master \]= master ~~ MANIFEST")
    assert message_recorder.find(r"\* repo_3   \[ master \]  master")
    # these should not be in output
    assert not message_recorder.find(r"\* repo_1")
    assert not message_recorder.find(r"\* repo_5")


def test_sync_on_groups_intersection__case_3_a(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Reason:

    when new Manifest (on different branch) does
    have different Groups defined, we may want
    to update them to config.
    If we do not do it, we can end up with error
    even for default listing.
    (only when 'clone_all_repos'=false)

    This is not desired and by default when
    no Groups are provided for 'tsrc sync',
    new Groups should be updated to config.

    We can still disable this behavior by providing:
    '--no-update-config' for 'tsrc sync' command

    And here we should test both cases if they
    work as declared.

    Cases:

    * 1st: plain sync
    * 2nd: sync with 'no-update-config'
    * 3rd: A: sync with 'ignore-missing-group'
    * 3rd: B: sync with 'ignore-missing-group', while provide 'groups'
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
    git_server.manifest.change_branch("master")
    manifest_url = git_server.manifest_url

    # 3rd: add bunch of Groups
    git_server.add_group("group_1", ["manifest", "repo_1"])
    git_server.add_group("group_3", ["manifest", "repo_3"])
    git_server.add_group("group_5", ["manifest", "repo_5"])

    # 4th: init Workspace with only selected Groups
    tsrc_cli.run("init", manifest_url, "--groups", "group_1", "group_3", "group_5")

    # 5th: save and push current Manifest to different Git Branch (dev)
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-B", "dev")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # 6th: clean tsrc configuration
    # rmtree(workspace_path / ".tsrc")
    move(workspace_path / ".tsrc", workspace_path / ".old_tsrc")

    # ================== from here it is different ==================
    # 7th: add some other groups
    git_server.add_group("group_2", ["manifest", "repo_2"])
    git_server.add_group("group_4", ["manifest", "repo_4"])
    git_server.add_group("group_6", ["manifest", "repo_6"])

    # 8th: init workspace with bunch of groups
    tsrc_cli.run(
        "init",
        "--branch",
        "master",
        manifest_url,
        "--groups",
        "group_2",
        "group_4",
        "group_6",
        "group_3",
    )

    # 9th: change branch for next sync
    tsrc_cli.run("manifest", "--branch", "dev")

    # ================== from here it is different ==================
    # 10th: sync (use specific case for given test)
    # case: 3 A
    # here: if we do not provide '--ignore-missing-groups'
    #   we will end up with error that 'group_2' is not found
    tsrc_cli.run("sync", "--ignore-missing-groups")

    # 11th: veryfy by 'status' output
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* manifest \[ master \]= master ~~ MANIFEST")
    assert message_recorder.find(r"\* repo_1   \[ master \]  master")
    assert message_recorder.find(r"\* repo_3   \[ master \]  master")
    assert message_recorder.find(r"\* repo_5   \[ master \]  master")


def test_sync_on_groups_intersection__case_3_b(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Reason:

    when new Manifest (on different branch) does
    have different Groups defined, we may want
    to update them to config.
    If we do not do it, we can end up with error
    even for default listing (tsrc status).
    (only when 'clone_all_repos'=false)

    This is not desired and by default when
    no Groups are provided for 'tsrc sync',
    new Groups should be updated to config.

    We can still disable this behavior by providing:
    '--no-update-config' for 'tsrc sync' command

    And here we should test both cases if they
    work as declared.

    Cases:

    * 1st: plain sync
    * 2nd: sync with 'no-update-config'
    * 3rd: A: sync with 'ignore-missing-group'
    * 3rd: B: sync with 'ignore-missing-group', while provide 'groups'
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
    git_server.manifest.change_branch("master")
    manifest_url = git_server.manifest_url

    # 3rd: add bunch of Groups
    git_server.add_group("group_1", ["manifest", "repo_1"])
    git_server.add_group("group_3", ["manifest", "repo_3"])
    git_server.add_group("group_5", ["manifest", "repo_5"])

    # 4th: init Workspace with only selected Groups
    tsrc_cli.run("init", manifest_url, "--groups", "group_1", "group_3", "group_5")

    # 5th: save and push current Manifest to different Git Branch (dev)
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-B", "dev")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # 6th: clean tsrc configuration
    # rmtree(workspace_path / ".tsrc")
    move(workspace_path / ".tsrc", workspace_path / ".old_tsrc")

    # ================== from here it is different ==================
    # 7th: add some other groups
    git_server.add_group("group_2", ["manifest", "repo_2"])
    git_server.add_group("group_4", ["manifest", "repo_4"])
    git_server.add_group("group_6", ["manifest", "repo_6"])

    # 8th: init workspace with bunch of groups
    tsrc_cli.run(
        "init",
        "--branch",
        "master",
        manifest_url,
        "--groups",
        "group_2",
        "group_4",
        "group_6",
        "group_3",
    )

    # 9th: change branch for next sync
    tsrc_cli.run("manifest", "--branch", "dev")

    # ================== from here it is different ==================
    # 10th: check if 'status' respects Groups
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(
        r"=> Destination \[Deep Manifest description\] \(Future Manifest description\)"
    )
    assert message_recorder.find(r"\* repo_2               \(        << master \)")
    assert message_recorder.find(r"\* repo_6               \(        << master \)")
    assert message_recorder.find(r"\* repo_4               \(        << master \)")
    assert message_recorder.find(
        r"\* manifest \[ master \]= \( master << dev \) \(expected: master\) ~~ MANIFEST"
    )
    assert message_recorder.find(r"\* repo_3   \[ master \]  \( master == master \)")
    assert not message_recorder.find(r"\* repo_5")
    assert not message_recorder.find(r"\* repo_1")

    # 11th: sync (use specific case for given test)
    # variant: 3 B
    # here: the 'group_2' is not configured,
    #   but with '--ignore-missing-groups' it will be ignored
    #   from provided list, and config will be updated only with
    #   proper Groups
    #   (skipping 'group_5' as it was not entered in '--groups')
    tsrc_cli.run(
        "sync", "--ignore-missing-groups", "--groups", "group_1", "group_2", "group_3"
    )

    # 12th: veryfy by 'status' output
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* manifest \[ master \]= master ~~ MANIFEST")
    assert message_recorder.find(r"\* repo_1   \[ master \]  master")
    assert message_recorder.find(r"\* repo_3   \[ master \]  master")
    # exclude
    assert not message_recorder.find(r"\* repo_5")


def test_sync_on_groups_intersection__case_3_b__no_update_config(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Reason:

    Test keeping config file ('.tsrc/config.yml')
    unchanged on 'sync'

    Such king of action have conquences.
    Like we may no longer use 'tsrc status' just like that.

    This si extension of earlier tests
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
    git_server.manifest.change_branch("master")
    manifest_url = git_server.manifest_url

    # 3rd: add bunch of Groups
    git_server.add_group("group_1", ["manifest", "repo_1"])
    git_server.add_group("group_3", ["manifest", "repo_3"])
    git_server.add_group("group_5", ["manifest", "repo_5"])

    # 4th: init Workspace with only selected Groups
    tsrc_cli.run("init", manifest_url, "--groups", "group_1", "group_3", "group_5")

    # 5th: save and push current Manifest to different Git Branch (dev)
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-B", "dev")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # 6th: clean tsrc configuration
    # rmtree(workspace_path / ".tsrc")
    move(workspace_path / ".tsrc", workspace_path / ".old_tsrc")

    # ================== from here it is different ==================
    # 7th: add some other groups
    git_server.add_group("group_2", ["manifest", "repo_2"])
    git_server.add_group("group_4", ["manifest", "repo_4"])
    git_server.add_group("group_6", ["manifest", "repo_6"])

    # 8th: init workspace with bunch of groups
    tsrc_cli.run(
        "init",
        "--branch",
        "master",
        manifest_url,
        "--groups",
        "group_2",
        "group_4",
        "group_6",
        "group_3",
    )

    # 9th: change branch for next sync
    tsrc_cli.run("manifest", "--branch", "dev")

    # 10th: sync without update config
    tsrc_cli.run(
        "sync",
        "--no-update-config",
        "--ignore-missing-groups",
        "--groups",
        "group_1",
        "group_2",
        "group_3",
    )
    # let us see what this does:
    # * 'group_1' gets ignored as it is not configured in workspace configuration ('.tsrc/config.yml')  # noqa E501
    # * 'group_2' gets ignored due to it is missing on Future Manifest
    # * skipping 'group_5' from Future Manifest as it was not present in '--groups'
    # * skipping 'group_6' from config ('.tsrc/config.yml') as it wos not present in '--groups'
    # * only 'group_3' is usefull than and thus synced

    # 11th: veryfy by 'status' output
    #   unline before, we have to use '--ignore-missing-groups', due to config file was not updated
    #   and old groups are present there
    message_recorder.reset()
    tsrc_cli.run("status", "--ignore-missing-groups")
    assert message_recorder.find(r"\* manifest \[ master \]= master ~~ MANIFEST")
    assert message_recorder.find(r"\* repo_3   \[ master \]  master")
    # exclude
    assert not message_recorder.find(r"\* repo_5")
    assert not message_recorder.find(r"\* repo_1")


def test_sync_on_groups_intersection__case_3_b__no_update_config__0_repos(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Reason:

    Our filters of Groups AND ignoring missing groups
    may lead 'sync' to 0 Repos.
    In such case further action should be stopped

    This si extension of earlier tests
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
    git_server.manifest.change_branch("master")
    manifest_url = git_server.manifest_url

    # 3rd: add bunch of Groups
    git_server.add_group("group_1", ["manifest", "repo_1"])
    git_server.add_group("group_3", ["manifest", "repo_3"])
    git_server.add_group("group_5", ["manifest", "repo_5"])

    # 4th: init Workspace with only selected Groups
    tsrc_cli.run("init", manifest_url, "--groups", "group_1", "group_3", "group_5")

    # 5th: save and push current Manifest to different Git Branch (dev)
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-B", "dev")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # 6th: clean tsrc configuration
    # rmtree(workspace_path / ".tsrc")
    move(workspace_path / ".tsrc", workspace_path / ".old_tsrc")

    # ================== from here it is different ==================
    # 7th: add some other groups
    git_server.add_group("group_2", ["manifest", "repo_2"])
    git_server.add_group("group_4", ["manifest", "repo_4"])
    git_server.add_group("group_6", ["manifest", "repo_6"])

    # 8th: init workspace with bunch of groups
    tsrc_cli.run(
        "init",
        "--branch",
        "master",
        manifest_url,
        "--groups",
        "group_2",
        "group_4",
        "group_6",
        "group_3",
    )

    # 9th: change branch for next sync
    tsrc_cli.run("manifest", "--branch", "dev")

    # 10th: sync without update config
    #   none of Groups are present in Future Manifest
    message_recorder.reset()
    tsrc_cli.run(
        "sync",
        "--no-update-config",
        "--ignore-missing-groups",
        "--groups",
        "group_2",
        "group_6",
    )
    assert message_recorder.find(r":: Nothing to synchronize, skipping")
