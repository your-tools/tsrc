from pathlib import Path
from shutil import move

# import pytest
import ruamel.yaml
from cli_ui.tests import MessageRecorder

from tsrc.git import run_git
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer
from tsrc.workspace_config import WorkspaceConfig


def test_basic_fm_groups(
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
    assert message_recorder.find(r"")

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
    assert message_recorder.find(r"\* repo_2   \[ master \]  \( master << ::: \)")

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
    assert message_recorder.find(r"=> Future Manifest's Repos found:")
    assert message_recorder.find(r"\* manifest \( master << ::: \) ~~ MANIFEST")
    assert message_recorder.find(r"\* repo_2   \( master << ::: \)")

    # 14th: b) check the same, but in 'tsrc manifest'
    #   here there should be only single record
    message_recorder.reset()
    tsrc_cli.run("manifest", "--groups", "group_7")
    assert message_recorder.find(r"=> Future Manifest's Repo found:")
    assert message_recorder.find(r"\* manifest \( master << ::: \) ~~ MANIFEST")
    assert not message_recorder.find(r"\* repo_2   \( master << ::: \)")

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
