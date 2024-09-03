"""
test_display_dm_fm_mm

collection of tests dedicated to displaying related to:
* Deep Manifest
* Future Manifest
* Manifest marker

contains:
##### Normal display (check alignment)
* 'test_status_2_x_mm': rare case of 2 MANIFEST markers
* 'test_status_dm_fm': general test of DM and FM integrated together
* 'test_status_cmd_param_3x_no': test all '--no-XX' cmd param options
* 'test_mm_alignment_in_all_types': test Manifest Marker alignment
* 'test_mm_alignment_in_all_types_2'
##### Errors on Manifest (that should be Warnings at best)
* 'test_dm_manifests_schema_error'
* 'test_fm_manifests_schema_error'
* 'test_dm_and_fm_manifests_mising_group_item'
"""

import os
from pathlib import Path
from shutil import move
from typing import List, Union

# import pytest
import ruamel.yaml
from cli_ui.tests import MessageRecorder

from tsrc.git import run_git
from tsrc.test.cli.test_groups_extra import ad_hoc_insert_to_manifests_groups
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer
from tsrc.workspace_config import WorkspaceConfig


def test_status_2_x_mm(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Purpose:

    verify how it will be shown (tsrc status)
    when there is Manifest repository integrated
    into the Workspace (DM), while Future Manifest (FM) will
    not include it on given destination,
    but will have it on different destination.
    In this case there will be:
    2 MANIFEST markers at the same time (rare case)

    Scenario:
    * 1st: Create repository
    * 2nd: add Manifest repository
    * 3rd: init workspace on master
    * 4th: manifest repo: checkout new branch <devel>
    * 5th: update manifest repo:
        change 'dest' for Manifest's repository and save
    * 6th: git push Manifest repo to origin:<devel>
    * 7th: manifest repo: checkout back to <master>
    * 8th: call manifest branch change to <devel>
    * 9th: see status output
    """

    # 1st: Create repository
    git_server.add_repo("repo1_long_long_long_name")
    git_server.push_file("repo1_long_long_long_name", "CMakeLists.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: checkout new branch <devel>
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-B", "devel")

    # 5th: update manifest repo:
    #    change 'dest' for Manifest's repository and save
    ad_hoc_update_dm_dest__for_status_2_x_mm(workspace_path)

    # 6th: git push Manifest repo to origin:<devel>
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "changing DM dest for the FM")
    run_git(manifest_path, "push", "-u", "origin", "devel")

    # 7th: manifest repo: checkout back to <master>
    run_git(manifest_path, "checkout", "master")

    # 8th: call manifest branch change to <devel>
    message_recorder.reset()
    tsrc_cli.run("manifest", "--branch", "devel")
    assert message_recorder.find(
        r"\* manifest       \[ master \]= \(        << master \) ~~ MANIFEST"
    )
    assert message_recorder.find(
        r"- FM_destination             \( master << ::: \)    ~~ MANIFEST"
    )

    # 9th: see status output
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(
        r"\* repo1_long_long_long_name \[ master \]  \( master == master \)"
    )
    assert message_recorder.find(
        r"\* manifest                  \[ master \]= \(        << master \) ~~ MANIFEST"
    )
    assert message_recorder.find(
        r"- FM_destination                        \( master << ::: \)    ~~ MANIFEST"
    )


def ad_hoc_update_dm_dest__for_status_2_x_mm(
    workspace_path: Path,
) -> None:
    """change Manifest's dest"""
    manifest_path = workspace_path / "manifest" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())

    for _, value in parsed.items():
        if isinstance(value, List):
            for x in value:
                if isinstance(x, ruamel.yaml.comments.CommentedMap):
                    if x["dest"] == "manifest":
                        x["dest"] = "FM_destination"
    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)


def test_status_dm_fm(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Reason:
    Perform general test of DM and FM.
    In particular verify:
    DM leftovers having FM description (apprise block) like:
    '* repo2    [ master ]  ( master << ::: )'
    And how it will be shown, where there is just DM leftover
    without FM description:
    '* repo3    [ master ]'
    And also test how it will end up when DM is disabled.

    Scenario:
    * 1st: Create repository
    * 2nd: add Manifest repository
    * 3rd: init workspace on master
    * 4th: manifest repo: checkout new branch <devel>
    * 5th: manifest repo:
        put some new repository there and commit and push
    * 6th: change manifest branch to <devel>
    * 7th: see the FM and DM if there is relation
    (as DM is already checked to new branch <devel>
    while FM is also pointing to new branch <devel>)
    * 8th: add another DM that does not have FM
    (and test output)
    * 9th: filtering test
        We now have 2 DM leftovers. One is also in FM.
        When we disable DM by '--no-dm' we should still
        have report from one that is in FM (as FM)
    """

    # 1st: Create repository
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: checkout new branch <devel>
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-B", "devel")

    # 5th: put some new repository there and commit and push
    ad_hoc_update_dm__for_status_dm_fm(workspace_path)
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "extending with new repo-2")
    run_git(manifest_path, "push", "-u", "origin", "devel")

    # 6th: change manifest branch to <devel>
    tsrc_cli.run("status")
    tsrc_cli.run("manifest", "--branch", "devel")

    # 7th: see the FM and DM if there is relation
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(
        r"- repo2    \[ master \]  \( master << ::: \)"
    ), "repo2 is leftover that is also present in Future Manifest"

    # 8th: add another DM that does not have FM
    ad_hoc_update_dm_2__for_status_dm_fm(workspace_path)
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"- repo3    \[ master \]")
    assert not message_recorder.find(
        r"- repo3    \[ master \]  \("
    ), "repo3 cannot have FM block included"

    # 9th: filtering test
    message_recorder.reset()
    tsrc_cli.run("status", "--no-dm")
    assert message_recorder.find(
        r"\* manifest \( master << devel \) \(dirty\) \(expected: master\) ~~ MANIFEST"
    )
    assert message_recorder.find(r"\* repo1    \( master == master \)")
    assert message_recorder.find(
        r"- repo2    \( master << ::: \)"
    ), "it does not find FM leftover"


def ad_hoc_update_dm__for_status_dm_fm(
    workspace_path: Path,
) -> None:
    manifest_path = workspace_path / "manifest" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())

    keep_url: Union[str, None] = None
    for _, value in parsed.items():
        if isinstance(value, List):
            for x in value:
                if isinstance(x, ruamel.yaml.comments.CommentedMap):
                    if x["dest"] == "repo1":
                        if x["url"]:
                            keep_url = x["url"]

    if keep_url:
        for _, value in parsed.items():
            if isinstance(value, List):
                value.append({"dest": "repo2", "url": keep_url})

    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)


def ad_hoc_update_dm_2__for_status_dm_fm(
    workspace_path: Path,
) -> None:
    manifest_path = workspace_path / "manifest" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())

    keep_url: Union[str, None] = None
    for _, value in parsed.items():
        if isinstance(value, List):
            for x in value:
                if isinstance(x, ruamel.yaml.comments.CommentedMap):
                    if x["dest"] == "repo1":
                        if x["url"]:
                            keep_url = x["url"]

    if keep_url:
        for _, value in parsed.items():
            if isinstance(value, List):
                value.append({"dest": "repo3", "url": keep_url})

    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)


def test_status_cmd_param_3x_no(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Purpose:

    verify if 3 command-line parameters works
    as design:
    '--no-dm' should suppress Deep Manifest block
    '--no-fm' should suppress Future Manifest printouts
    '--no-mm' should suppress Manifest marker display

    Note:

    inspired by 'test_status_2_dm.py'

    Scenario:
    * 1st: Create repository
    * 2nd: add Manifest repository
    * 3rd: init workspace on master
    * 4th: manifest repo: checkout new branch <devel>
    * 5th: update manifest repo:
        change 'dest' for Manifest's repository and save
    * 6th: git push Manifest repo to origin:<devel>
    * 7th: manifest repo: checkout back to <master>
    * 8th: call manifest branch change to <devel>
    * 9th:
        * A: status output without MANIFEST marker
        * B: status output without Future Manifest
        * C: status output without Deep Manifest
        * combinations:
            * D: B + C
    """

    # 1st: Create repository
    git_server.add_repo("repo1_long_long_long_name")
    git_server.push_file("repo1_long_long_long_name", "CMakeLists.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: checkout new branch <devel>
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-B", "devel")

    # 5th: update manifest repo:
    #   change 'dest' for Manifest's repository and save
    #   reusing same Fn as for 'status_2_x_mm'
    ad_hoc_update_dm_dest__for_status_2_x_mm(workspace_path)

    # 6th: git push Manifest repo to origin:<devel>
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "changing DM dest for the FM")
    run_git(manifest_path, "push", "-u", "origin", "devel")

    # 7th: manifest repo: checkout back to <master>
    run_git(manifest_path, "checkout", "master")

    # 8th: call manifest branch change to <devel>
    tsrc_cli.run("manifest", "--branch", "devel")

    # 9th:
    #   A: status output without MANIFEST marker
    message_recorder.reset()
    tsrc_cli.run("status", "--no-mm")
    assert message_recorder.find(
        r"\* repo1_long_long_long_name \[ master \]  \( master == master \)"
    ), "issue on option: A"
    assert message_recorder.find(
        r"\* manifest                  \[ master \]= \(        << master \)"
    ), "issue on option: A"
    assert message_recorder.find(
        r"- FM_destination                        \( master << ::: \)"
    ), "issue on option: A"

    #   B: status output without Future Manifest
    message_recorder.reset()
    tsrc_cli.run("status", "--no-fm")
    assert message_recorder.find(
        r"\* repo1_long_long_long_name \[ master \]  master"
    ), "issue on option: B"
    assert message_recorder.find(
        r"\* manifest                  \[ master \]= master ~~ MANIFEST"
    ), "issue on option: B"

    #   C: status output without Deep Manifest
    message_recorder.reset()
    tsrc_cli.run("status", "--no-dm")
    assert message_recorder.find(
        r"\* repo1_long_long_long_name \( master == master \)"
    ), "issue on option: C"
    assert message_recorder.find(
        r"\* manifest                  \(        << master \) ~~ MANIFEST"
    ), "issue on option: C"
    assert message_recorder.find(
        r"- FM_destination            \( master << ::: \)    ~~ MANIFEST"
    ), "issue on option: C"

    #       D: B + C
    message_recorder.reset()
    tsrc_cli.run("status", "--no-dm", "--no-fm")
    assert message_recorder.find(r"\* repo1_long_long_long_name master")
    assert message_recorder.find(r"\* manifest                  master ~~ MANIFEST")


def test_mm_alignment_in_all_types(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Reason:

    Test Manifest Marker alignment
    in all types (LM, DM, FM)

    Manifest Marker should be aligned to
    * Git Description or
    * Apprise branch block
        (if FM is enabled and Manifest branch is in changing state)

    Scenario:

    * 1st: Create repositories and Manifest repository as well
        (use 'manifest-dm' as 'dest' for Manifest's repo)
    * 2nd: init Workspace on master
    * 3rd: Manifest repo: checkout new branch <devel>
    * 4th: Update Manifest's repo:
        change 'dest' from 'manifest-dm' to 'manifest'
    * 5th: Manifest's repo: commit + push
    * 6th: verify `tsrc status`
    * 7th: verify `tsrc manifest`
    * 8th: manifest's repo: checkout new branch <future_b>
    * 9th: 'manifest.yml': update 'dest' of Manifest's repo
    * 10th: Manifest's repo: add, commit and push
    * 11th: enter to Manifest's branch changing state
    * 12th: check 'status'
        also change local git branch of Manifest's repo
        so there can be all 3 Manifest Markers in output
    * 13th: A: test alignment of local Manifest's Manifest Marker
    * 13th: B: same for 'manifest' command
    """
    # 1st: Create repositories and Manifest repository as well
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "CMakeLists.txt")
    manifest_url = git_server.manifest_url
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 2nd: init Workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 3rd: Manifest repo: checkout new branch <devel>
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-B", "devel")

    # 4th: Update Manifest's repo:
    ad_hoc_update_to_dm_dest__for_test_mm(workspace_path)

    # 5th: Manifest's repo: commit + push
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "go devel branch")
    run_git(manifest_path, "push", "-u", "origin", "devel")

    # 6th: verify `tsrc status`
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"- manifest-dm \[ master \]        ~~ MANIFEST")
    assert message_recorder.find(r"\* repo2       \[ master \] master")
    assert message_recorder.find(r"\* repo1       \[ master \] master")
    assert message_recorder.find(
        r"\* manifest               devel \(expected: master\) ~~ MANIFEST"
    )

    # 7th: verify `tsrc manifest`
    message_recorder.reset()
    tsrc_cli.run("manifest")
    assert message_recorder.find(r"=> Before possible GIT statuses, Workspace reports:")
    assert message_recorder.find(r"=> Destination \[Deep Manifest description\]")
    assert message_recorder.find(
        r"\* manifest               devel \(expected: master\) ~~ MANIFEST"
    )
    assert message_recorder.find(r"- manifest-dm \[ master \]       ~~ MANIFEST")

    # 8th: manifest's repo: checkout new branch <future_b>
    run_git(manifest_path, "checkout", "-B", "future_b")

    # 9th: 'manifest.yml': update 'dest' of Manifest's repo
    ad_hoc_update_to_fm_dest__for_test_mm(workspace_path)

    # 10th: Manifest's repo: add, commit and push
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "go devel branch")
    run_git(manifest_path, "push", "-u", "origin", "future_b")

    # 11th: enter to Manifest's branch changing state
    message_recorder.reset()
    tsrc_cli.run("manifest", "--branch", "future_b")
    assert message_recorder.find(
        r"=> Destination \[Deep Manifest description\] \(Future Manifest description\)"
    )
    assert message_recorder.find(
        r"\* manifest               \(        << future_b \) \(expected: master\) ~~ MANIFEST"
    )
    assert message_recorder.find(
        r"- manifest-fm \[ master \] \( master << ::: \)      ~~ MANIFEST"
    )

    # 12th: check 'status'
    run_git(manifest_path, "checkout", "devel")
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(
        r"=> Destination \[Deep Manifest description\] \(Future Manifest description\)"
    )
    assert message_recorder.find(
        r"\* manifest               \(        << devel \) \(expected: master\) ~~ MANIFEST"
    )
    assert message_recorder.find(r"\* repo2       \[ master \] \( master == master \)")
    assert message_recorder.find(r"\* repo1       \[ master \] \( master == master \)")
    assert message_recorder.find(
        r"- manifest-dm \[ master \]                      ~~ MANIFEST"
    )
    assert message_recorder.find(
        r"- manifest-fm            \( master << ::: \)    ~~ MANIFEST"
    )

    # 13th: A: test alignment of local Manifest's Manifest Marker
    repo2_path = workspace_path / "repo2"
    run_git(
        repo2_path,
        "checkout",
        "-B",
        "too_long_git_branch_to_test_alignment_of_lm_on_mm",
    )
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(
        r"\* manifest               \(        << devel \) \(expected: master\)                          ~~ MANIFEST"  # noqa: E501
    )
    assert message_recorder.find(
        r"\* repo2       \[ master \] \( master << too_long_git_branch_to_test_alignment_of_lm_on_mm \) \(expected: master\) \(missing upstream\)"  # noqa: E501
    )
    assert message_recorder.find(
        r"- manifest-dm \[ master \]                                                                 ~~ MANIFEST"  # noqa: E501
    )
    assert message_recorder.find(
        r"- manifest-fm            \( master << ::: \)                                               ~~ MANIFEST"  # noqa: E501
    )
    assert message_recorder.find(r"\* repo1       \[ master \] \( master == master \)")

    # 13th: B: same for 'manifest' command
    message_recorder.reset()
    tsrc_cli.run("manifest")
    assert message_recorder.find(
        r"\* manifest               \(        << devel \) \(expected: master\) ~~ MANIFEST"
    )
    assert message_recorder.find(
        r"- manifest-dm \[ master \]                     ~~ MANIFEST"
    )
    assert message_recorder.find(
        r"- manifest-fm            \( master << ::: \)   ~~ MANIFEST"
    )


def test_mm_alignment_in_all_types_2(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Reason:

    Test Manifest Marker alignment
    in all types (LM, DM, FM)

    Manifest Marker should be aligned to
    * Git Description or
    * Apprise branch block
        (if FM is enabled and Manifest branch is in changing state)

    Scenario:

    * 1st: Create repositories and Manifest repository as well
        (use 'manifest-dm' as 'dest' for Manifest's repo)
    * 2nd: init Workspace on master
    * 3rd: Manifest repo: checkout new branch <devel>
    * 4th: Update Manifest's repo:
        change 'dest' from 'manifest-dm' to 'manifest'
    * 5th: Manifest's repo: commit + push
    * 6th: verify `tsrc status`
    * 7th: verify `tsrc manifest`
    * 8th: manifest's repo: checkout new branch <future_b>
    * 9th: 'manifest.yml': update 'dest' of Manifest's repo
    * 10th: Manifest's repo: add, commit and push
    * 11th: enter to Manifest's branch changing state
    * 12th: check 'status'
    * 13th: clone manifest repo to tmp folder
        and move it to Workspace as: "manifest-dm"
    * 14th: A: test DM's MM alignment with short branch name
    * 14th: B: do the same with XLL branch name
    * 15th: sync
    * 16th: verify 'status' output after sync for alignment
    """
    # 1st: Create repositories and Manifest repository as well
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "CMakeLists.txt")
    manifest_url = git_server.manifest_url
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 2nd: init Workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 3rd: Manifest repo: checkout new branch <devel>
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-B", "devel")

    # 4th: Update Manifest's repo:
    ad_hoc_update_to_dm_dest__for_test_mm(workspace_path)

    # 5th: Manifest's repo: commit + push
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "go devel branch")
    run_git(manifest_path, "push", "-u", "origin", "devel")

    # 6th: verify `tsrc status`
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"- manifest-dm \[ master \]        ~~ MANIFEST")
    assert message_recorder.find(r"\* repo2       \[ master \] master")
    assert message_recorder.find(r"\* repo1       \[ master \] master")
    assert message_recorder.find(
        r"\* manifest               devel \(expected: master\) ~~ MANIFEST"
    )

    # 7th: verify `tsrc manifest`
    message_recorder.reset()
    tsrc_cli.run("manifest")
    assert message_recorder.find(r"=> Before possible GIT statuses, Workspace reports:")
    assert message_recorder.find(r"=> Destination \[Deep Manifest description\]")
    assert message_recorder.find(
        r"\* manifest               devel \(expected: master\) ~~ MANIFEST"
    )
    assert message_recorder.find(r"- manifest-dm \[ master \]       ~~ MANIFEST")

    # 8th: manifest's repo: checkout new branch <future_b>
    run_git(manifest_path, "checkout", "-B", "future_b")

    # 9th: 'manifest.yml': update 'dest' of Manifest's repo
    ad_hoc_update_to_fm_dest__for_test_mm(workspace_path)

    # 10th: Manifest's repo: add, commit and push
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "go devel branch")
    run_git(manifest_path, "push", "-u", "origin", "future_b")

    # 11th: enter to Manifest's branch changing state
    message_recorder.reset()
    tsrc_cli.run("manifest", "--branch", "future_b")
    assert message_recorder.find(
        r"=> Destination \[Deep Manifest description\] \(Future Manifest description\)"
    )
    assert message_recorder.find(
        r"\* manifest               \(        << future_b \) \(expected: master\) ~~ MANIFEST"
    )
    assert message_recorder.find(
        r"- manifest-fm \[ master \] \( master << ::: \)      ~~ MANIFEST"
    )

    # 12th: check 'status'
    run_git(manifest_path, "checkout", "devel")
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(
        r"=> Destination \[Deep Manifest description\] \(Future Manifest description\)"
    )
    assert message_recorder.find(
        r"\* manifest               \(        << devel \) \(expected: master\) ~~ MANIFEST"
    )
    assert message_recorder.find(r"\* repo2       \[ master \] \( master == master \)")
    assert message_recorder.find(r"\* repo1       \[ master \] \( master == master \)")
    assert message_recorder.find(
        r"- manifest-dm \[ master \]                      ~~ MANIFEST"
    )
    assert message_recorder.find(
        r"- manifest-fm            \( master << ::: \)    ~~ MANIFEST"
    )

    # 13th: clone manifest repo to tmp folder
    #   and move it to Workspace as: "manifest-dm"
    tmp_path: Path = workspace_path / "tmp"
    os.mkdir(tmp_path)
    run_git(tmp_path, "clone", manifest_url)
    dm_path: Path = workspace_path / "manifest-dm"
    move(tmp_path / "manifest", dm_path)

    # 14th: A: test DM's MM alignment with short branch name
    run_git(dm_path, "checkout", "-b", "t")
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* repo2       \[ master \] \( master == master \)")
    assert message_recorder.find(r"\* repo1       \[ master \] \( master == master \)")
    assert message_recorder.find(
        r"\+ manifest-dm \[ master \] \(        << t \)      ~~ MANIFEST"
    )
    assert message_recorder.find(
        r"\* manifest               \(        << devel \) \(expected: master\) ~~ MANIFEST"
    )
    assert message_recorder.find(
        r"- manifest-fm            \( master << ::: \)    ~~ MANIFEST"
    )

    # 14th: B: do the same with XLL branch name
    run_git(dm_path, "checkout", "-b", "too_long_branch_to_test_that_should_exceed")
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(
        r"\* manifest               \(        << devel \) \(expected: master\)                   ~~ MANIFEST"  # noqa: E501
    )
    assert message_recorder.find(
        r"- manifest-fm            \( master << ::: \)                                        ~~ MANIFEST"  # noqa: E501
    )
    assert message_recorder.find(
        r"\+ manifest-dm \[ master \] \(        << too_long_branch_to_test_that_should_exceed \) ~~ MANIFEST"  # noqa: E501
    )
    assert message_recorder.find(r"\* repo1       \[ master \] \( master == master \)")
    assert message_recorder.find(r"\* repo2       \[ master \] \( master == master \)")

    # 15th: sync
    tsrc_cli.run("sync")

    # 16th: verify 'status' output after sync for alignment
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\+ manifest    \[ master \] devel  ~~ MANIFEST")
    assert message_recorder.find(r"\* manifest-fm            master ~~ MANIFEST")
    assert message_recorder.find(r"\* repo1       \[ master \] master")
    assert message_recorder.find(r"\* repo2       \[ master \] master")


def ad_hoc_update_to_dm_dest__for_test_mm(
    workspace_path: Path,
) -> None:
    """change Manifest's dest"""
    manifest_path = workspace_path / "manifest" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())

    for _, value in parsed.items():
        if isinstance(value, List):
            for x in value:
                if isinstance(x, ruamel.yaml.comments.CommentedMap):
                    if x["dest"] == "manifest":
                        x["dest"] = "manifest-dm"
    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)


def ad_hoc_update_to_fm_dest__for_test_mm(
    workspace_path: Path,
) -> None:
    """change Manifest's dest"""
    manifest_path = workspace_path / "manifest" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())

    for _, value in parsed.items():
        if isinstance(value, List):
            for x in value:
                if isinstance(x, ruamel.yaml.comments.CommentedMap):
                    if x["dest"] == "manifest-dm":
                        x["dest"] = "manifest-fm"
    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)


def test_dm_manifests_schema_error(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Test how does 'status' get over the damaged Deep Manifest

    Scenario:
    * 1st: Create repositories and Manifest repository as well
    * 2nd: init Workspace on master
    * 3rd: damage Manifest file (on purpose)
    * 4th: see if 'status' warns about it, while still prints the rest
    """
    # 1st: Create repositories and Manifest repository as well
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "CMakeLists.txt")
    manifest_url = git_server.manifest_url
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 2nd: init Workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 3rd: damage Manifest file (on purpose)
    ad_hoc_delete_item_from_manifest(workspace_path)

    # 4th: see if 'status' warns about it, while still prints the rest
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"Warning: Failed to get Deep Manifest")
    assert message_recorder.find(r"\* manifest master \(dirty\) ~~ MANIFEST")
    assert message_recorder.find(r"\* repo1    master")
    assert not message_recorder.find(r"=> Destination .*")


def test_fm_manifests_schema_error(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Test is damaged Future Manifest does not cause terminating issue

    Scenario:

    # 1st: Create repositories and Manifest repository as well
    # 2nd: init Workspace on master
    # 3rd: Manifest repo: checkout new branch: 'damaged'
    # 4th: damage Manifest's repo
    # 5th: Manifest's repo: commit + push
    # 6th: go back to 'master' for Manifest's repo
    # 7th: switch future branch to 'damaged'
    # 8th: verify if 'status' return proper Warning
    """
    # 1st: Create repositories and Manifest repository as well
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "CMakeLists.txt")
    manifest_url = git_server.manifest_url
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 2nd: init Workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 3rd: Manifest repo: checkout new branch: 'damaged'
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-B", "damaged")

    # 4th: damage Manifest's repo
    ad_hoc_delete_item_from_manifest(workspace_path)

    # 5th: Manifest's repo: commit + push
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "go devel branch")
    run_git(manifest_path, "push", "-u", "origin", "damaged")

    # 6th: go back to 'master' for Manifest's repo
    run_git(manifest_path, "checkout", "master")

    # 7th: switch future branch to 'damaged'
    #   also with Warning
    message_recorder.reset()
    tsrc_cli.run("manifest", "--branch", "damaged")
    assert message_recorder.find(r"Warning: Failed to get Future Manifest")
    assert message_recorder.find(r"\* manifest \[ master \]= master ~~ MANIFEST")

    # 8th: verify if 'status' return proper Warning
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"Warning: Failed to get Future Manifest")
    assert message_recorder.find(r"\* manifest \[ master \]= master ~~ MANIFEST")
    assert message_recorder.find(r"\* repo1    \[ master \]  master")


def ad_hoc_delete_item_from_manifest(
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
                    if x["dest"] == "repo1":
                        del x["url"]

    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)


def test_dm_and_fm_manifests_mising_group_item(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Simulate the case when Deem Manifest or Future Manifest
    have Group with Item (Repo) that is not present.

    Under normal circumstances this is Error, but
    when we are talking about DM or FM, it should be just a Warning
    as data from DM and FM are NOT mandatory as such.

    So let us check if we can see the Warning

    Scenario
    # 1st: create a bunch of repos
    # 2nd: add Manifest
    # 3rd: add Group
    # 4th: init Workspace
    # 5th: checkout and push 'dev' branch of Manifest
    # 6th: add Group with non-existing item (Repo)
    # 7th: see if we have DM Warning
    # 8th: set manifest branch to change to 'dev'
    # 9th: go back to 'master' for Manifest repo
    # 10th: add non-existent item to Group in Future Manifest
    # 11th: check for Warking on FM, disabling FM to update
    """

    # 1st: create a bunch of repos
    git_server.add_repo("repo_2")
    git_server.push_file("repo_2", "my_file_in_repo_2.txt")
    git_server.add_repo("repo_3")
    git_server.push_file("repo_3", "my_file_in_repo_3.txt")

    # 2nd: add Manifest
    git_server.add_manifest_repo("manifest")
    manifest_url = git_server.manifest_url

    # 3rd: add Group
    git_server.add_group("g23", ["repo_2", "repo_3"])

    # 4th: init Workspace
    tsrc_cli.run("init", manifest_url, "--branch", "master")

    # 5th: checkout and push 'dev' branch of Manifest
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-b", "dev")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # 6th: add Group with non-existing item (Repo)
    ad_hoc_insert_to_manifests_groups(workspace_path / "manifest" / "manifest.yml")

    # 7th: see if we have DM Warning
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(
        r"Warning: Deep Manifest: Groups: cannot add 'repo_1' to 'gm'"
    )

    # 8th: set manifest branch to change to 'dev'
    tsrc_cli.run("manifest", "--branch", "dev")

    # 9th: go back to 'master' for Manifest repo
    run_git(manifest_path, "checkout", "master")
    run_git(manifest_path, "commit", "-a", "-m", "pre Group's missing item")
    run_git(manifest_path, "push", "-u", "origin", "master")

    # 10th: add non-existent item to Group in Future Manifest
    ad_hoc_insert_to_manifests_groups(
        workspace_path / ".tsrc" / "future_manifest" / "manifest.yml"
    )

    # 11th: check for Warking on FM, disabling FM to update
    message_recorder.reset()
    tsrc_cli.run("status", "--same-fm")
    assert message_recorder.find(
        r"Warning: Future Manifest: Groups: cannot add 'repo_1' to 'gm'"
    )
