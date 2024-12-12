"""
Test how Groups are taken care of when
'dump-manifest' command is in UPDATE mode

as only than the Groups can be taken into account

normal Repo grabbing (RAW or Workspace) cannot obtain
Groups.

Someone may say, that Workspace Grab can work with Groups,
as they can be obtained from config. This is wrong as
such Groups does not contain items, therefore are
useles in this case.

However Workspace config can be updated

Contains:
* test_dump_manifest__constraints__no_remote_must_match_dest__on_update
* test_dump_manifest_workspace__update_with_constraints__add_repo
* test_dump_manifest_workspace__groups_delete
* test_dump_manifest__rename_repo
"""

import os
from pathlib import Path
from typing import List

# import pytest
import ruamel.yaml
from cli_ui.tests import MessageRecorder

from tsrc.dump_manifest import ManifestDumper
from tsrc.dump_manifest_args_data import ManifestDataOptions
from tsrc.dump_manifest_helper import MRISHelpers
from tsrc.git import run_git
from tsrc.manifest import Manifest, load_manifest, load_manifest_safe_mode
from tsrc.manifest_common_data import ManifestsTypeOfData
from tsrc.repo import Remote, Repo
from tsrc.test.cli.test_dump_manifest import ad_hoc_delete_remote_from_manifest
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer
from tsrc.workspace_config import WorkspaceConfig

# from tsrc.test.helpers.message_recorder_ext import MessageRecorderExt


# @pytest.mark.last
def test_dump_manifest_raw__constraints__incl_excl(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    test if include_regex|eclude_regex also work
    when on RAW dump (without update)

    filtering works only for Repo's dest, filtering
    by previous directories names (if present) is not possible

    Scenario:

    * 1st: create repositories representing project
    * 2nd: add there a Manifest Repo
    * 3rd: init Workspace
    * 4th: dump manifest: test (only) exclude
    * 5th: dump_manifest: test include_regex and exclude_regex
    * 6th: dump_manifest: test when we exclude everything
    """
    # 1st: create repositories representing project
    git_server.add_repo("frontend-proj")
    git_server.push_file("frontend-proj", "frontend-proj.txt")
    git_server.add_repo("backend-proj")
    git_server.push_file("backend-proj", "backend-proj.txt")
    git_server.add_repo("extra-lib")
    git_server.push_file("extra-lib", "extra-lib.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add there a Manifest Repo
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init Workspace
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: dump manifest: test (only) exclude
    tsrc_cli.run(
        "dump-manifest", "--raw", ".", "-e", "extra|proj", "--save-to", "m_1.yml"
    )

    m_1_file = workspace_path / "m_1.yml"
    if m_1_file.is_file() is False:
        raise Exception("Manifest file does not exists")
    m_1 = load_manifest(m_1_file)  # this Manifest should be fine
    m_1_repos = m_1.get_repos()
    count: int = 0
    for repo in m_1_repos:
        if repo.dest == "manifest":
            count += 1
        else:
            count += 2
    if count != 1:
        raise Exception("Manifest repo contains wrong items")

    # 5th: dump_manifest: test include_regex and exclude_regex
    tsrc_cli.run(
        "dump-manifest",
        "--raw",
        ".",
        "-i",
        "extra|proj",
        "-e",
        "backend",
        "--save-to",
        "m_2.yml",
    )

    m_2_file = workspace_path / "m_2.yml"
    if m_2_file.is_file() is False:
        raise Exception("Manifest file does not exists")
    m_2 = load_manifest(m_2_file)  # this Manifest should be fine
    m_2_repos = m_2.get_repos()
    count = 0
    for repo in m_2_repos:
        if repo.dest == "frontend-proj":
            count += 1
        elif repo.dest == "extra-lib":
            count += 2
        else:
            count += 4
    if count != 3:
        raise Exception("Manifest repo contains wrong items")

    # 6th: dump_manifest: test when we exclude everything
    message_recorder.reset()
    tsrc_cli.run(
        "dump-manifest", "--raw", ".", "-i", "extra", "-e", "extra", "--preview"
    )
    message_recorder.find(r"=> No Repos were found")


def test_dump_manifest__constraints__no_remote_must_match_dest__on_update(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    if we are performing UPDATE on Manifest and some Repo
    does not have remotes (so it is hard to identify it)
    we should use 'dest' instead and update it accordingly

    Scenario:

    * 1st: add few Repos
    * 2nd: add Manifest repository
    * 3rd: add Groups (to test constraints)
    * 4th: init workspace on master
    * 5th: delete remote of one Repo of Deep Manifest
    * 6th: commit and push Deep Manifest
    * 7th: create new manifest providing different Groups
    * 8th: verify Manifest created by Group 1
    * 9th: verify Manifest created by Group 2
    """
    # 1st: add few Repos
    git_server.add_repo("repo1-mr")
    git_server.push_file("repo1-mr", "test_1-mr.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "test2.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: add Groups (to test constraints)
    git_server.add_group("group_1", ["manifest", "repo1-mr"])
    git_server.add_group("group_2", ["manifest", "repo2"])

    # 4th: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)

    # 5th: delete remote of one Repo of Deep Manifest
    manifest_path_file = workspace_path / "manifest" / "manifest.yml"
    ad_hoc_delete_remote_from_manifest(manifest_path_file)

    # 6th: commit and push Deep Manifest
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "adding repo without url")
    run_git(manifest_path, "push", "-u", "origin", "master")

    # 7th: create new manifest providing different Groups
    tsrc_cli.run(
        "dump-manifest", "--update", "--save-to", "manifest_g_1.yml", "-g", "group_1"
    )
    tsrc_cli.run(
        "dump-manifest", "--update", "--save-to", "manifest_g_2.yml", "-g", "group_2"
    )

    # 8th: verify Manifest created by Group 1
    #   it should update remote on 'repo1-mr'
    m_1_file = workspace_path / "manifest_g_1.yml"
    if m_1_file.is_file() is False:
        raise Exception("Manifest file does not exists")
    # m_1 = load_manifest_safe_mode(m_1_file, ManifestsTypeOfData.SAVED)
    m_1 = load_manifest(m_1_file)  # this Manifest should be fine
    count: int = 0
    for repo in m_1.get_repos():
        if repo.dest == "repo1-mr":
            if repo.remotes:
                count += 1
        elif repo.dest == "repo2":
            count += 2
        elif repo.dest == "manifest":
            count += 4
        else:
            raise Exception("Manifest contain wrong item")
    if count != 7:
        raise Exception("Manifest does not contain all items")

    # 9th: verify Manifest created by Group 2
    #   it should NOT update remote on 'repo1-mr'
    m_2_file = workspace_path / "manifest_g_2.yml"
    if m_2_file.is_file() is False:
        raise Exception("Manifest file 2 does not exists")
    m_2 = load_manifest_safe_mode(m_2_file, ManifestsTypeOfData.SAVED)
    count = 0
    for repo in m_2.get_repos():
        if repo.dest == "repo1-mr":
            if not repo.remotes:
                count += 1
        elif repo.dest == "repo2":
            count += 2
        elif repo.dest == "manifest":
            count += 4
        else:
            raise Exception("Manifest contain wrong item")
    if count != 7:
        raise Exception("Manifest does not contain all items")


def test_dump_manifest_workspace__update_with_constraints__add_repo(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    test selective Adding new Repo when on
    RAW dump + UPDATE mode + user-provided Groups
    (thus with constraints)

    Story:

    when using RAW dump and UPDATE and we want
    to limit such update on selected Group(s),
    then other Repos that does not match such
    Group(s) should be left alone (not updated).
    However when there is Repo in Manifest we
    are updating, that is not found in such Manifest,
    and at the same time was found by RAW dump,
    this is sign that such Repo should be Added
    (since it is clearly missing from Manifest)
    Hovever if we did not use such Group, when
    such Repo is included, there should be no Addition

    Scenario:

    * 1st: Create bunch of repos
    * 2nd: add Manifest repo
    * 3rd: add bunch of Groups
    * 4th: init workspace with only selected group
    * 5th: push current manifest as git branch "working"
    * 6th: go back to Manifest's Git branch "master"
    * 7th: adding Group, with non-existant Repo dest
    * 8th: ugly sync, as there is non-existant Repo 'repo_3x' as item in Group
    * 9th: change back to "working" branch and 'sync'
    * 10th: now go to Manifest with 'repo_3x' in Groups
    * 11th: ad-hoc create 'repo_3x', GIT init, add, commit, set remote
    * 12th: RAW dump when with Group 'group_1'
    * 13th: checking if 'repo_3x' is NOT there
    * 14th: another RAW dump when with Group 'group_3'
    * 15th: checking if 'repo_3x' is there, if not, it is FAIL
    """
    # 1st: Create bunch of repos
    git_server.add_repo("repo_1")
    git_server.push_file("repo_1", "my_file_in_repo_1.txt")
    git_server.add_repo("repo_2")
    git_server.push_file("repo_2", "my_file_in_repo_2.txt")
    git_server.add_repo("repo_3")
    git_server.push_file("repo_3", "my_file_in_repo_3.txt")
    repo_4_url = git_server.add_repo("repo_4")
    git_server.push_file("repo_4", "my_file_in_repo_4.txt")

    # 2nd: add Manifest repo
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")
    manifest_url = git_server.manifest_url

    # 3rd: add bunch of Groups
    git_server.add_group("group_1", ["manifest", "repo_1", "repo_3"])
    git_server.add_group("group_3", ["manifest", "repo_3"])

    # 4th: init workspace with only selected group
    tsrc_cli.run(
        "init",
        "--branch",
        "master",
        manifest_url,
        "--clone-all-repos",
        "--groups",
        "group_1",
        "group_3",
    )

    # 5th: push current manifest as git branch "working"
    manifest_path = workspace_path / "manifest"
    manifest_path_file = workspace_path / "manifest" / "manifest.yml"
    run_git(manifest_path, "checkout", "-b", "working")
    ad_hoc_update_manifest_repo(manifest_path_file, manifest_url, "working")
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "new_manifest")
    run_git(manifest_path, "push", "-u", "origin", "working")

    # 6th: go back to Manifest's Git branch "master"
    run_git(manifest_path, "checkout", "master")

    # 7th: adding Group, with non-existant Repo dest
    #   we will return to this later
    git_server.add_group(
        "group_3", ["manifest", "repo_3", "repo_3x"], do_add_repos=False
    )

    # 8th: ugly sync, as there is non-existant Repo 'repo_3x' as item in Group
    tsrc_cli.run("sync", "--ignore-missing-groups", "--ignore-missing-group-items")

    # 9th: change back to "working" branch and 'sync'
    #   still we have to ignore missing group item as there is still 'repo_3x'
    #   and to avoid further Errors on reading Deep Manifest
    #   and after the branch change even an Error on Future Manifest,
    #   we should disable thouse as well ('--no-dm', '--no-fm')
    tsrc_cli.run(
        "manifest",
        "--ignore-missing-group-items",
        "--no-dm",
        "--no-fm",
        "--branch",
        "working",
    )
    tsrc_cli.run("sync")

    # 10th: now go to Manifest with 'repo_3x' in Groups
    #   We are now in clean working state, no missing Group item
    #   is present, however if checkout "master" branch of Manifest
    #   we will introduce non-existant Repo 'repo_3x' again,
    #   this time only to Deep Manifest.
    #   Now when we call RAW dump + UPDATE + Group constraints
    #   when our Group selection will contain 'group_3' where
    #   the 'repo_3x' is included, than only in this case
    #   the 'dump-manifest' will add this Repo when on Group constraints
    run_git(manifest_path, "checkout", "master")

    # 11th: ad-hoc create 'repo_3x', GIT init, add, commit, set remote
    #   So from this point forward, the 'repo_3x' exists.
    #   It is not present in the Workspace, but we will be using
    #   RAW dump anyway
    sub1_1_path = Path("repo_3x")
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)
    full1_path: Path = Path(os.path.join(workspace_path, sub1_1_path))
    run_git(full1_path, "init")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full1_path, "add", "in_repo.txt")
    run_git(full1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    run_git(full1_path, "remote", "add", "origin", repo_4_url)

    # 12th: RAW dump when with Group 'group_1'
    #   First, let us try how RAW dump + UPDATE + Group constraints
    #   DOES NOT add 'repo_3x' as it is not included in 'group_1' items.
    os.chdir(workspace_path)
    tsrc_cli.run(
        "dump-manifest",
        "--raw",
        ".",
        "--update",
        "--save-to",
        "manifest_g_1.yml",
        "-g",
        "group_1",
    )

    # 13th: checking if 'repo_3x' is NOT there
    w_m_path = workspace_path / "manifest_g_1.yml"
    m = load_manifest_safe_mode(w_m_path, ManifestsTypeOfData.LOCAL)
    for repo in m.get_repos():
        if repo.dest == "repo_3x":
            raise Exception("failed Manifest update on repos of Group 'group_1'")

    # 14th: another RAW dump when with Group 'group_3'
    #   Here in Group 'group_3', the 'repo_3x' IS PRESENT
    #   therefore RAW dump + UPDATE + Group constraints
    #   should add it as new item to Repos
    tsrc_cli.run(
        "dump-manifest",
        "--raw",
        ".",
        "--update",
        "--save-to",
        "manifest_g_3.yml",
        "-g",
        "group_3",
    )

    # 15th: checking if 'repo_3x' is there, if not, it is FAIL
    w_m_path = workspace_path / "manifest_g_3.yml"
    m = load_manifest_safe_mode(w_m_path, ManifestsTypeOfData.LOCAL)
    match_repo_3x: bool = False
    for repo in m.get_repos():
        if repo.dest == "repo_3x":
            match_repo_3x = True
    if match_repo_3x is False:
        raise Exception("failed Manifest update on repos of Group 'group_3'")


def test_dump_manifest_workspace__groups_delete(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    # TODO: test it also when cloning all Repos
    #   this should include 'repo_4' as well
    """
    when deleting Repos, it should also be deleted
    from Group's 'repos:'. this test verifies that

    Scenario:

    * 1st: Create bunch of repos
    * 2nd: add Manifest repo
    * 3rd: add bunch of Groups
    * 4th: init workspace with only selected group
    * 5th: edit Manifest: remove Repo
    * 6th: checkout new branch, commit, push Manifest
    * 7th: tsrc sync new branch
    * 8th: checkout manifest branch back
    * 9th: tsrc dump-manifest '--update'
    * 10th: use 'load_manifest to verify Deep Manfiest
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

    # 2nd: add Manifest repo
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")
    manifest_url = git_server.manifest_url

    # 3rd: add bunch of Groups
    git_server.add_group("group_1", ["manifest", "repo_1", "repo_3"])
    git_server.add_group("group_3", ["repo_3"])

    # 4th: init workspace with only selected group
    tsrc_cli.run(
        "init", "--branch", "master", manifest_url, "--groups", "group_1", "group_3"
    )

    # 5th: edit Manifest: remove Repo
    manifest_file_path = workspace_path / "manifest" / "manifest.yml"
    ad_hoc_delete_repo_from_manifest(manifest_file_path)

    # 6th: checkout new branch, commit, push Manifest
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-b", "without_3")
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "without_3")
    run_git(manifest_path, "push", "-u", "origin", "without_3")

    # 7th: tsrc sync new branch
    tsrc_cli.run("manifest", "-b", "without_3")
    tsrc_cli.run("sync")

    # 8th: checkout manifest branch back
    run_git(manifest_path, "checkout", "master")

    # 9th: tsrc dump-manifest '--update'
    tsrc_cli.run("dump-manifest", "--update")
    #   so it should delete from 'manifest.yml'
    #   and thus delete from Groups as well

    # 10th: use 'load_manifest to verify Deep Manfiest
    #   'repo_3' should not be there anymore
    #   not even amont the group's elements
    w_m_path = workspace_path / "manifest" / "manifest.yml"
    m = load_manifest(w_m_path)
    if m.group_list:
        for element in m.group_list.all_elements:
            if element == "repo_3":
                raise Exception("failed Manifest update on group items")
    for repo in m.get_repos():
        if repo.dest == "repo_3":
            raise Exception("failed Manifest update on repos")


def test_dump_manifest__rename_repo(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    test feature for Rename Repos's dest
    it also renames Repo's dest of Groups

    Scenario

    * 1st: Create bunch of repos
    * 2nd: add Manifest repo
    * 3rd: add bunch of Groups
    * 4th: init workspace with only selected group
    * 5th: edit Manifest: remove Repo
    * 6th: checkout new branch, commit, push Manifest
    * 7th: tsrc sync new branch
    * 8th: checkout manifest branch back
    * 9th: rename bunch of Repos's dest
    * 10th: tsrc dump-manifest RAW '--update'
    * 11th: verify by load_manifest: Groups.elements
    * 12th: verify by load_manifest: Repos's dest vs URL
    """

    # 1st: Create bunch of repos
    #   also: intentionaly put there 'repo_4-7509f8e'
    #   as it is exact first replacement name for
    #   'repo_4' and thus also test generation
    #   of new replacement name
    repo_1_url = git_server.add_repo("repo_1")
    git_server.push_file("repo_1", "my_file_in_repo_1.txt")
    git_server.add_repo("repo_2")
    git_server.push_file("repo_2", "my_file_in_repo_2.txt")
    repo_3_url = git_server.add_repo("repo_3")
    git_server.push_file("repo_3", "my_file_in_repo_3.txt")
    repo_4_url = git_server.add_repo("repo_4")
    git_server.push_file("repo_4", "my_file_in_repo_4.txt")
    git_server.add_repo("repo_5")
    git_server.push_file("repo_5", "my_file_in_repo_4.txt")
    git_server.add_repo("repo_4-7509f8e")
    git_server.push_file("repo_4-7509f8e", "my_file_in_repo_4.txt")

    # 2nd: add Manifest repo
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")
    manifest_url = git_server.manifest_url

    # 3rd: add bunch of Groups
    git_server.add_group("group_1", ["manifest", "repo_1", "repo_3"])
    git_server.add_group("group_3", ["repo_3"])

    # 4th: init workspace with only selected group
    tsrc_cli.run(
        "init",
        "--branch",
        "master",
        manifest_url,
        "--clone-all-repos",
        "--groups",
        "group_1",
        "group_3",
    )

    # 5th: edit Manifest: remove Repo
    manifest_file_path = workspace_path / "manifest" / "manifest.yml"
    ad_hoc_delete_repo_from_manifest(manifest_file_path)

    # 6th: checkout new branch, commit, push Manifest
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-b", "without_3")
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "without_3")
    run_git(manifest_path, "push", "-u", "origin", "without_3")

    # 7th: tsrc sync new branch
    tsrc_cli.run("manifest", "-b", "without_3")
    tsrc_cli.run("sync")

    # 8th: checkout manifest branch back
    run_git(manifest_path, "checkout", "master")

    # 9th: rename bunch of Repos's dest
    os.rename("repo_1", "repo_1_renamed")
    os.rename("repo_4", "repo_1")
    os.rename("repo_1_renamed", "repo_4")
    #   one more without colision
    os.rename("repo_3", "repo_3x")

    # 10th: tsrc dump-manifest RAW '--update'
    tsrc_cli.run("dump-manifest", "--raw", ".", "--update")

    # 11th: verify by load_manifest: Groups.elements
    m = load_manifest(manifest_file_path)
    _part_11(m)

    # 12th: verify by load_manifest: Repos's dest vs URL
    _part_12(m, repo_1_url, repo_3_url, repo_4_url)


def _part_11(m: Manifest) -> None:
    is_ok: int = 0
    if m.group_list and m.group_list.groups:
        for g in m.group_list.groups:
            for ge in m.group_list.groups[g].elements:
                if g == "group_1":
                    if ge == "manifest":
                        is_ok += 1
                    elif ge == "repo_4":
                        is_ok += 2
                    elif ge == "repo_3x":
                        is_ok += 4
                    else:
                        is_ok = -1000
                elif g == "group_3":
                    if ge == "repo_3x":
                        is_ok += 8
                else:
                    is_ok = -1000
    if is_ok != 15:
        raise Exception("Manifest's Groups items mismach")


# flake8: noqa: C901
def _part_12(m: Manifest, repo_1_url: str, repo_3_url: str, repo_4_url: str) -> None:
    is_ok: int = 0
    repos = m.get_repos(all_=True)
    for repo in repos:
        if repo.dest == "repo_1" and repo.clone_url == repo_4_url:
            is_ok += 1
        elif repo.dest == "repo_3x" and repo.clone_url == repo_3_url:
            is_ok += 2
        elif repo.dest == "repo_4" and repo.clone_url == repo_1_url:
            is_ok += 4
        elif repo.dest == "repo_2":
            is_ok += 8
        elif repo.dest == "repo_5":
            is_ok += 16
        elif repo.dest == "repo_4-7509f8e":
            is_ok += 32
        elif repo.dest == "manifest":
            is_ok += 64
        else:
            is_ok = -1000
    if is_ok != 127:
        raise Exception("Manifest's Repo mismatch")


def ad_hoc_delete_repo_from_manifest(
    manifest_path: Path,
) -> None:
    """
    this time we will call function
    that deletes from manifest
    """
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    y = yaml.load(manifest_path.read_text())

    del_list: List[str] = ["repo_3"]

    is_updated_tmp: List[bool] = [False]  # dummy
    m_d = ManifestDumper()
    m_d._walk_yaml_delete_group_items(y, 0, False, False, del_list, is_updated_tmp)
    m_d._walk_yaml_delete_repos_items(y, 0, False, del_list, is_updated_tmp)

    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(y, file)


def ad_hoc_update_manifest_repo(
    manifest_path: Path,
    manifest_url: str,
    manifest_branch: str,
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    y = yaml.load(manifest_path.read_text())

    u_m_list: List[str] = ["manifest"]

    repos: List[Repo] = [
        Repo(
            dest="manifest",
            remotes=[Remote(name="origin", url=manifest_url)],
            branch=manifest_branch,
        )
    ]

    mris_h = MRISHelpers(repos=repos)
    mris = mris_h.mris

    is_updated_tmp: List[bool] = [False]  # dummy
    m_d = ManifestDumper()
    mdo = ManifestDataOptions()
    m_d._walk_yaml_update_repos_items(y, 0, mris, mdo, False, u_m_list, is_updated_tmp)

    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(y, file)
