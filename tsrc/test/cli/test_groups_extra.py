from pathlib import Path
from shutil import move
from typing import List

import pytest
import ruamel.yaml
from cli_ui.tests import MessageRecorder

from tsrc.git import run_git
from tsrc.manifest_common import ManifestGroupNotFound
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer
from tsrc.workspace_config import WorkspaceConfig


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
    assert message_recorder.find(r"=> Before possible GIT statuses, Workspace reports:")
    assert message_recorder.find(r"=> Destination \[Deep Manifest description\]")
    assert message_recorder.find(r"\* manifest \[ master \]= master ~~ MANIFEST")
    assert message_recorder.find(r"\* repo_3   \[ master \]  master")
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
    assert message_recorder.find(r"=> Before possible GIT statuses, Workspace reports:")
    assert message_recorder.find(r"=> Destination \[Deep Manifest description\]")
    assert message_recorder.find(r"\* manifest \[ master \]= master ~~ MANIFEST")
    assert message_recorder.find(r"\* repo_3   \[ master \]  master")
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


def test_intersectioned_groups(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Reason:

    verify how status displays DM and FM when
    Groups will be in consideration. As when
    Workspace is in state of Manifest branch change,
    Groups needs to be considered from 2 sides:
    From Workspace side and from Future Manifest side.
    Also Groups comes also to account for Deep Manifest
    as Deep Manifest also needs to consider intersection
    of the Groups provided and in Deep Manifest.
    Handling Groups should mimic default behavior of status
    like when '--clone-all-repos' are provided, all
    defined repos should be considered. This should be done
    also in Deep Manifest and in Future Manifest.

    Scenario:
    * 1st: Create bunch of repos
    * 2nd: add Manifest repo
    * 3rd: add bunch of Groups
    * 4th: init Workspace with only selected Groups
    * 5th: save and push current Manifest to different Git Branch (dev)
    * 6th: see status
    * 7th: clean tsrc config and 'repo_2'
    * 8th: add extra 'repo_6' and 'group_6'
    * 9th: 'init' again with only selected groups
    * 10th: see status now
    * 11th: now change back to previous branch of Manifest: 'dev'
    * 12th: check status of only 'group_7'
    * 13th: delete group_7 from local Manifest
    * 14th: a) check status of only 'group_7' again
    * 14th: b) check the same, but in 'tsrc manifest'
    * 14th: c) just ignore detecting GIT description for leftovers
    * 15th: revert Manifest branch back to 'master'
    * 16th: check status of only 'group_7' again

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
    git_server.add_group("inc_group", ["repo_3"])
    git_server.add_group("group_2", ["manifest", "repo_4"])
    git_server.add_group("group_3", ["manifest", "repo_5"])
    git_server.add_group("group_4", ["repo_3", "repo_1", "repo_5"])
    git_server.add_group("group_7", ["manifest", "repo_2"])

    git_server.manifest.configure_group(
        "group_1", ["repo_1", "manifest"], includes=["inc_group"]
    )

    # 4th: init Workspace with only selected Groups
    tsrc_cli.run(
        "init",
        "--branch",
        "master",
        manifest_url,
        "--clone-all-repos",
        "--groups",
        "group_1",
        "group_3",
        "group_4",
    )
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 5th: save and push current Manifest to different Git Branch (dev)
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-B", "dev")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # 6th: see status
    #   We have cloned all repos, but configuration is only using
    #   selected groups: 'group_1','group_3','group_4'
    #   which translated to:
    #   'repo_1','manifest','repo_3','repo_5'
    #   However:
    #   configuration also have 'clone_all_repos'=True
    #   Therefore:
    #   we should consider all defined repository for Deep Manifest as well
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* repo_1   \[ master \]  master")
    assert message_recorder.find(r"\* repo_2   \[ master \]  master")
    assert message_recorder.find(r"\* repo_3   \[ master \]  master")
    assert message_recorder.find(r"\* repo_4   \[ master \]  master")
    assert message_recorder.find(r"\* repo_5   \[ master \]  master")
    assert message_recorder.find(
        r"\* manifest \[ master \]= dev \(expected: master\) ~~ MANIFEST"
    )

    # 7th: clean tsrc config and 'repo_2'
    #   as this allows us to call 'init' again
    #   now without '--clone-all-repos'
    # rmtree(workspace_path / ".tsrc")
    # rmtree(workspace_path / "repo_2")
    move(workspace_path / ".tsrc", workspace_path / ".old_tsrc")
    move(workspace_path / "repo_2", workspace_path / "old_repo_2")

    # 8th: add extra 'repo_6' and 'group_6'
    #   as such repo and group will not be in Manifest
    #   pushed to branch: 'dev' and it will end up in Manifest
    #   on branch 'master'
    git_server.add_repo("repo_6")
    git_server.push_file("repo_6", "my_file_in_repo_6.txt")
    git_server.add_group("group_6", ["manifest", "repo_6"])

    # 9th: 'init' again with only selected groups
    #   groups: 'group_2','group_3','group_6'
    #   which translated to:
    #   'manifest','repo_4','repo_5','repo_6'
    tsrc_cli.run(
        "init",
        "--branch",
        "master",
        manifest_url,
        "--groups",
        "group_2",
        "group_3",
        "group_6",
    )

    # 10th: see status now
    #   now the configured group(s) has to be respected, thus status
    #   displays only these 4 repos, and look!
    #   'repo_6' is not in the Deep Manifest,
    #   as it is checked out to branch: 'dev'
    #   which does not contains 'repo_6'
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* repo_4   \[ master \]  master")
    assert message_recorder.find(r"\* repo_5   \[ master \]  master")
    assert message_recorder.find(r"\* repo_6               master")
    assert message_recorder.find(
        r"\* manifest \[ master \]= dev \(expected: master\) ~~ MANIFEST"
    )

    # 11th: now change back to previous branch of Manifest: 'dev'
    message_recorder.reset()
    tsrc_cli.run("manifest", "--branch", "dev")
    assert message_recorder.find(
        r"\* manifest \[ master \]= \( master << dev \) \(expected: master\) ~~ MANIFEST"
    )

    # 12th: check status of only 'group_7'
    #   this translated to:
    #   'manifest','repo_2'
    #   OH NO! what happend?!
    #   we have require status of the repo, that is not checked-out,
    #   thus we are rightly receive an error
    #   However:
    #   even if 'repo_2' thrown and error, the data from Deep Manifest (DM)
    #   and even from Future Manifest (FM) is there!
    #   Therefore:
    #   we will have 2 records for 'repo_2':
    #       * one with error
    #       * one with DM and FM
    message_recorder.reset()
    tsrc_cli.run("status", "--groups", "group_7")
    assert message_recorder.find(r"\* repo_2               error: .* does not exist")
    assert message_recorder.find(
        r"\* manifest \[ master \]= \( master << dev \) \(expected: master\) ~~ MANIFEST"
    )
    assert message_recorder.find(r"- repo_2   \[ master \]  \( master << ::: \)")

    # 13th: delete group_7 from local Manifest
    #   Let us now not consider 'repo_2' for Workpace.
    #   By removing it from local manifest,
    #   by removing the group: 'group_7' where it is included,
    #   while having 'group_7' defined only in Future Manifest
    #   we will force only Future Manifest leftovers output
    ad_hoc_update_lm_groups(workspace_path)

    # 14th: a) check status of only 'group_7' again
    #   As local manifest does no longer have 'group_7'
    #   defined, only option left is Future Manifest
    #   a) also check header of Workspace report
    message_recorder.reset()
    tsrc_cli.run("status", "--groups", "group_7")
    assert message_recorder.find(r"=> Only leftovers were found, containing:")
    assert message_recorder.find(r"=> Destination \(Future Manifest description\)")
    assert message_recorder.find(r"\+ manifest \( master << dev \) ~~ MANIFEST")
    assert message_recorder.find(r"- repo_2   \( master << ::: \)")

    # 14th: b) check the same, but in 'tsrc manifest'
    #   here there should be only single record
    message_recorder.reset()
    tsrc_cli.run("manifest", "--groups", "group_7")
    assert message_recorder.find(r"=> Only leftovers were found, containing:")
    assert message_recorder.find(r"=> Destination \(Future Manifest description\)")
    assert message_recorder.find(r"\+ manifest \( master << dev \) ~~ MANIFEST")
    assert not message_recorder.find(r"repo_2")

    # 14th: c) just ignore detecting GIT description for leftovers
    message_recorder.reset()
    tsrc_cli.run("status", "--strict", "--groups", "group_7")
    assert message_recorder.find(r"=> Only leftovers were found, containing:")
    assert message_recorder.find(r"=> Destination \(Future Manifest description\)")
    assert message_recorder.find(r"- manifest \( master << ::: \) ~~ MANIFEST")
    assert message_recorder.find(r"- repo_2   \( master << ::: \)")

    # 15th: revert Manifest branch back to 'master'
    message_recorder.reset()
    tsrc_cli.run("manifest", "--branch", "master")
    assert message_recorder.find(
        r"\* manifest \[ master \]= dev \(expected: master\) ~~ MANIFEST"
    )

    # 16th: check status of only 'group_7' again
    #   Now when there is no Future Manifest,
    #   ask Manifest branch is not set to change
    #   we rightly end up with the empty Worskpace
    message_recorder.reset()
    # "group_7" should not be found
    with pytest.raises(ManifestGroupNotFound):
        tsrc_cli.run("status", "--groups", "group_7")
    assert message_recorder.find(r"=> Workspace is empty")


def ad_hoc_update_lm_groups(
    workspace_path: Path,
) -> None:
    """perform ad-hoc update on local Manifest file.
    it deletes group_7 for testing purposes"""
    manifest_path = workspace_path / ".tsrc" / "manifest" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())

    for key, value in parsed.items():
        if key == "groups":
            do_delete: bool = False
            for i_key, _ in value.items():
                if i_key == "group_7":
                    do_delete = True

            if do_delete is True:
                del value["group_7"]

    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)


def test_dm_group_must_match(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Reason:

    Test if Deep Manifest's Group match,
    even if it is ONLY in Deep Manifest,
    so ManifestGroupNotFound will not be emited.

    Also test if missing group is reported properly.

    Scenario:

    * 1st: create a bunch of repos
    * 2nd: add Manifest repo on 'dev'
    * 3rd: add 'g1' Group to 'dev'
    * 4th: init Workspace from 'dev' branch
    * 5th: enter into Manifest branch change to 'master'
    * 6th: filter by Group 'g1'
    * 7th: side check: check Exception
    * 8th: sync, so checkout 'master' branch
    * 9th: now we should not be able to find 'g1' Group
        as it is not even in Deep Manifest.
        But let us see if we can change that in next step
    * 10th: Manifest Repo: checkout remote branch: 'dev'
    * 11th: verify status
    * 12th: Group 'g1' should match Deep Manifst's leftovers only
    """

    # 1st: create a bunch of repos
    git_server.add_repo("repo_1")
    git_server.push_file("repo_1", "my_file_in_repo_1.txt")
    git_server.add_repo("repo_2")
    git_server.push_file("repo_2", "my_file_in_repo_2.txt")
    git_server.add_repo("repo_3")
    git_server.push_file("repo_3", "my_file_in_repo_3.txt")

    # 2nd: add Manifest repo on 'dev'
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("dev")
    manifest_url = git_server.manifest_url

    # 3rd: add 'g1' Group to 'dev'
    git_server.add_group("g1", ["repo_1", "repo_2"])

    # 4th: init Workspace from 'dev' branch
    tsrc_cli.run("init", manifest_url, "--branch", "dev")

    # 5th: enter into Manifest branch change to 'master'
    message_recorder.reset()
    tsrc_cli.run("manifest", "--branch", "master")
    assert message_recorder.find(r"=> Before possible GIT statuses, Workspace reports:")
    assert message_recorder.find(
        r"=> Destination \[Deep Manifest description\] \(Future Manifest description\)"
    )
    assert message_recorder.find(
        r"\* manifest \[ master \]= \( master == master \) ~~ MANIFEST"
    )

    # 6th: filter by Group 'g1'
    message_recorder.reset()
    tsrc_cli.run("status", "-g", "g1")
    assert message_recorder.find(r"=> Before possible GIT statuses, Workspace reports:")
    assert message_recorder.find(r"=> Destination \(Future Manifest description\)")
    assert message_recorder.find(r"\+ manifest \( master == master \) ~~ MANIFEST")
    assert message_recorder.find(r"\+ repo_3   \( master == master \)")
    assert message_recorder.find(r"\* repo_2   \( master == master \)")
    assert message_recorder.find(r"\* repo_1   \( master == master \)")

    # 7th: side check: check Exception
    message_recorder.reset()
    with pytest.raises(ManifestGroupNotFound):
        tsrc_cli.run("status", "-g", "not_existent")

    # 8th: sync, so checkout 'master' branch
    tsrc_cli.run("sync")

    # 9th: now we should not be able to find 'g1' Group
    with pytest.raises(ManifestGroupNotFound):
        tsrc_cli.run("status", "-g", "g1")

    # 10th: Manifest Repo: checkout remote branch: 'dev'
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "branch", "dev", "origin/dev")
    run_git(manifest_path, "checkout", "dev")

    # 11th: verify status
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"=> Before possible GIT statuses, Workspace reports:")
    assert message_recorder.find(r"=> Destination \[Deep Manifest description\]")
    assert message_recorder.find(
        r"\* manifest \[ master \]= dev \(expected: master\) ~~ MANIFEST"
    )
    assert message_recorder.find(r"\* repo_1   \[ master \]  master")
    assert message_recorder.find(r"\* repo_2   \[ master \]  master")
    assert message_recorder.find(r"\* repo_3   \[ master \]  master")

    # 12th: Group 'g1' should match Deep Manifst's leftovers only
    message_recorder.reset()
    tsrc_cli.run("status", "-g", "g1")
    assert message_recorder.find(r"=> Only leftovers were found, containing:")
    assert message_recorder.find(r"=> Destination \[Deep Manifest description\]")
    assert message_recorder.find(r"\+ repo_1 \[ master \] master")
    assert message_recorder.find(r"\+ repo_2 \[ master \] master")
    # also must exclude
    assert not message_recorder.find(r"\* repo_3")
    assert not message_recorder.find(r"\* manifest")


def test_leftovers_only_for_dm_fm_git_desc(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Reason:

    Test pure leftovers printouts in case there are:
    * Deep Manifest desc is present for given Group
    * also Future Manifest desc is present for the same
    * not only that! but also repository is present
        in the Workspace (it should not without previous
        checkout in some step) so we also have
        + GIT description for the same

    Scenario:

    * 1st: create a bunch of repos
    * 2nd: add Manifest repo on 'dev'
    * 3rd: add 'g1' Group to 'dev'
    * 4th: init Workspace from 'dev' branch
    * 5th: enter into Manifest branch change to 'master'
    * 6th: sync, so checkout 'master' branch
    * 7th: Manifest Repo: checkout remote branch: 'dev'
    * 8th: Group 'g1' should match Deep Manifst's leftovers only
    * 9th: checkout 'future' branch of manifest
    * 10th: insert new Group 'gm' to 'future' branch
    * 11th: add, commit and push it to remote
    * 12th: change manifest branch to 'future'
    * 13th: check it: we should now have leftovers with future manifest desc
    * 14th: change DM branch to test alignment
    """

    # 1st: create a bunch of repos
    git_server.add_repo("repo_1")
    git_server.push_file("repo_1", "my_file_in_repo_1.txt")
    git_server.add_repo("repo_2")
    git_server.push_file("repo_2", "my_file_in_repo_2.txt")
    git_server.add_repo("repo_3")
    git_server.push_file("repo_3", "my_file_in_repo_3.txt")

    # 2nd: add Manifest repo on 'dev'
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("dev")
    manifest_url = git_server.manifest_url

    # 3rd: add 'g1' Group to 'dev'
    git_server.add_group("g1", ["repo_1", "repo_2"])

    # 4th: init Workspace from 'dev' branch
    tsrc_cli.run("init", manifest_url, "--branch", "dev")

    # 5th: enter into Manifest branch change to 'master'
    message_recorder.reset()
    tsrc_cli.run("manifest", "--branch", "master")
    assert message_recorder.find(r"=> Before possible GIT statuses, Workspace reports:")
    assert message_recorder.find(
        r"=> Destination \[Deep Manifest description\] \(Future Manifest description\)"
    )
    assert message_recorder.find(
        r"\* manifest \[ master \]= \( master == master \) ~~ MANIFEST"
    )

    # 6th: sync, so checkout 'master' branch
    tsrc_cli.run("sync")

    # 7th: Manifest Repo: checkout remote branch: 'dev'
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "branch", "dev", "origin/dev")
    run_git(manifest_path, "checkout", "dev")

    # 8th: Group 'g1' should match Deep Manifst's leftovers only
    message_recorder.reset()
    tsrc_cli.run("status", "-g", "g1")
    assert message_recorder.find(r"=> Only leftovers were found, containing:")
    assert message_recorder.find(r"=> Destination \[Deep Manifest description\]")
    assert message_recorder.find(r"\+ repo_1 \[ master \] master")
    assert message_recorder.find(r"\+ repo_2 \[ master \] master")
    # also must exclude
    assert not message_recorder.find(r"\* repo_3")
    assert not message_recorder.find(r"\* manifest")

    # 9th: checkout 'future' branch of manifest
    run_git(manifest_path, "checkout", "-b", "fu")

    # 10th: insert new Group 'gm' to 'future' branch
    ad_hoc_insert_to_dm_groups(workspace_path)

    # 11th: add, commit and push it to remote
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "'new group gm for future manifest'")
    run_git(manifest_path, "push", "-u", "origin", "fu")

    # 12th: change manifest branch to 'future'
    tsrc_cli.run("manifest", "--branch", "fu")

    # 13th: check it: we should now have leftovers with future manifest desc
    message_recorder.reset()
    tsrc_cli.run("status", "--group", "gm")
    assert message_recorder.find(r"\+ repo_1   \[ master \] \( master == master \)")
    assert message_recorder.find(
        r"\+ manifest \[ master \] \( master << fu \)     ~~ MANIFEST"
    )

    # 14th: change DM branch to test alignment
    ad_hoc_update_dm_branch(workspace_path)
    message_recorder.reset()
    tsrc_cli.run("status", "--group", "gm")
    assert message_recorder.find(r"\+ repo_1   \[ master \] \( master == master \)")
    assert message_recorder.find(
        r"\+ manifest \[ br     \] \( master << fu \)     ~~ MANIFEST"
    )


def ad_hoc_insert_to_dm_groups(
    workspace_path: Path,
) -> None:
    """
    insert 'gm' Group into deep manifest's manifest.yml file
    such 'gm' Group contains 'repo_1' and 'manifest'
    """
    manifest_path = workspace_path / "manifest" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())

    for key, value in parsed.items():
        if key == "groups":
            value.insert(1, "gm", {"repos": ["repo_1", "manifest"]})
            break

    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)


def ad_hoc_update_dm_branch(
    workspace_path: Path,
) -> None:
    manifest_path = workspace_path / "manifest" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())

    for _, value in parsed.items():
        if isinstance(value, List):
            for x in value:
                if isinstance(x, ruamel.yaml.comments.CommentedMap):
                    # if x["dest"] == "repo_1":
                    if x["dest"] == "manifest":
                        x["branch"] = "br"

    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)
