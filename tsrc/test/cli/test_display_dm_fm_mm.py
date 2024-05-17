"""
test_display_dm_fm_mm

collection of tests dedicated to displaying related to:
* Deep Manifest
* Future Manifest
* Manifest marker

contains:
* 'test_status_2_x_mm': rare case of 2 MANIFEST markers
* 'test_status_dm_fm': general test of DM and FM integrated together
* 'test_status_cmd_param_3xm': test all '--no-XX' cmd param options
"""

from pathlib import Path
from typing import List

import pytest
import ruamel.yaml
from cli_ui.tests import MessageRecorder

from tsrc.git import run_git
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
    ad_hoc_update_dm_dest(workspace_path)

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
        r"\* FM_destination             \( master << ::: \) ~~ MANIFEST"
    )

    # 9th: see status output
    print("DEBUG path =", workspace_path)
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(
        r"\* repo1_long_long_long_name \[ master \]  \( master == master \)"
    )
    assert message_recorder.find(
        r"\* manifest                  \[ master \]= \(        << master \) ~~ MANIFEST"
    )
    assert message_recorder.find(
        r"\* FM_destination                        \( master << ::: \) ~~ MANIFEST"
    )


def ad_hoc_update_dm_dest(
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


@pytest.mark.last
def test_status_dm_fm(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Reason:
    Perform general test of DM and FM.
    In particular: see how DM leftovers will have relation to FM:
    '* repo2    [ master ]  ( master << ::: )'
    And how it will be shown, where there is just DM leftover
    without FM relation:
    '* repo3    [ master ]'

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
    ad_hoc_update_dm(workspace_path)
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
        r"\* repo2    \[ master \]  \( master << ::: \)"
    ), "repo2 is leftover that is also present in Future Manifest"

    # 8th: add another DM that does not have FM
    ad_hoc_update_dm_2(workspace_path)
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* repo3    \[ master \]")
    assert not message_recorder.find(
        r"\* repo3    \[ master \]  \("
    ), "repo3 cannot have FM block included"


def ad_hoc_update_dm(
    workspace_path: Path,
) -> None:
    manifest_path = workspace_path / "manifest" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())

    keep_url: str
    for _, value in parsed.items():
        if isinstance(value, List):
            for x in value:
                if isinstance(x, ruamel.yaml.comments.CommentedMap):
                    if x["dest"] == "repo1":
                        if x["url"]:
                            keep_url = x["url"]

    print("DEBUG keep_url =", keep_url)

    for _, value in parsed.items():
        if isinstance(value, List):
            value.append({"dest": "repo2", "url": keep_url})
            # value.append({'dest': 'repo3', 'url': keep_url})
            # print("DEBUG  value =", value)
            # for x in value:
            #    print("DEBUG         x =", x)

    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)


def ad_hoc_update_dm_2(
    workspace_path: Path,
) -> None:
    manifest_path = workspace_path / "manifest" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())

    keep_url: str
    for _, value in parsed.items():
        if isinstance(value, List):
            for x in value:
                if isinstance(x, ruamel.yaml.comments.CommentedMap):
                    if x["dest"] == "repo1":
                        if x["url"]:
                            keep_url = x["url"]

    print("DEBUG keep_url =", keep_url)

    for _, value in parsed.items():
        if isinstance(value, List):
            # value.append({'dest': 'repo2', 'url': keep_url})
            value.append({"dest": "repo3", "url": keep_url})
            # print("DEBUG  value =", value)
            # for x in value:
            #    print("DEBUG         x =", x)

    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)


def test_status_cmd_param_3xm(
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
    #    change 'dest' for Manifest's repository and save
    ad_hoc_update_dm_dest(workspace_path)

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
    print("DEBUG path =", workspace_path)
    message_recorder.reset()
    tsrc_cli.run("status", "--no-mm")
    assert message_recorder.find(
        r"\* repo1_long_long_long_name \[ master \]  \( master == master \)"
    )
    assert message_recorder.find(
        r"\* manifest                  \[ master \]= \(        << master \)"
    )
    assert message_recorder.find(
        r"\* FM_destination                        \( master << ::: \)"
    )

    #   B: status output without Future Manifest
    message_recorder.reset()
    tsrc_cli.run("status", "--no-fm")
    assert message_recorder.find(r"\* repo1_long_long_long_name \[ master \]  master")
    assert message_recorder.find(
        r"\* manifest                  \[ master \]= master ~~ MANIFEST"
    )
    assert message_recorder.find(
        r"\* FM_destination                        ~~ MANIFEST"
    )

    #   C: status output without Deep Manifest
    message_recorder.reset()
    tsrc_cli.run("status", "--no-dm")
    assert message_recorder.find(r"\* repo1_long_long_long_name \( master == master \)")
    assert message_recorder.find(
        r"\* manifest                  \(        << master \) ~~ MANIFEST"
    )
    assert message_recorder.find(
        r"\* FM_destination            \( master << ::: \) ~~ MANIFEST"
    )

    #       D: B + C
    message_recorder.reset()
    tsrc_cli.run("status", "--no-dm", "--no-fm")
    assert message_recorder.find(r"\* repo1_long_long_long_name master")
    assert message_recorder.find(r"\* manifest                  master ~~ MANIFEST")
    assert message_recorder.find(r"\* FM_destination            ~~ MANIFEST")
