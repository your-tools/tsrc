"""
tests dedicated to 'sync --switch' mode

in such mode, the sync is about to change configuration for some
items like 'groups'. if such configuration is not found
in the Manifest file, and '--switch' is used non the less, the
default configuration for such configuration items is used.
(the default configuration is no Groups)

changing configuration is particulary usefull when we want to
switch to different manifest branch, that may have majority
of Repos/Groups different. this allows to not risk that such
current configuration will interfere with the Manifest's
own Groups settings (like it should not)

while without '--switch' the sync mechanizm consider
current configuration and new Manifest in default way
to keep prefered behavior by default.
"""

import os
import shutil
from pathlib import Path

import pytest
from cli_ui.tests import MessageRecorder

from tsrc.git import run_git
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer
from tsrc.workspace_config import WorkspaceConfig


def test_sync__switch__cfg_groups__to__no_m_sw_cfg_groups__with_cmd_groups(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Alias:

    Configured groups --> no manifest switch option

    Conditions:

    * Workspace with configured groups
    * FM does not contain any 'switch' part
    * FM groups does not intersect

    Outcome:

    * Workspace configuration of groups cleared
    """
    sub1_path = workspace_path
    sub1_1_path = Path("repo_1")
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)
    full_sub1_path: Path = Path(os.path.join(workspace_path, sub1_path, sub1_1_path))
    run_git(full_sub1_path, "init")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full_sub1_path, "add", "in_repo.txt")
    run_git(full_sub1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub1_1_url = git_server.get_url(str(sub1_1_path))
    sub1_1_url_path = Path(git_server.url_to_local_path(sub1_1_url))
    sub1_1_url_path.mkdir()
    run_git(sub1_1_url_path, "init", "--bare")
    run_git(full_sub1_path, "remote", "add", "origin", sub1_1_url)
    run_git(full_sub1_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    sub2_path = workspace_path
    sub2_1_path = Path("repo_2")
    os.mkdir(sub2_1_path)
    os.chdir(sub2_1_path)
    full_sub2_path: Path = Path(os.path.join(workspace_path, sub2_path, sub2_1_path))
    run_git(full_sub2_path, "init")
    sub2_1_1_file = Path("in_repo.txt")
    sub2_1_1_file.touch()
    run_git(full_sub2_path, "add", "in_repo.txt")
    run_git(full_sub2_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub2_1_url = git_server.get_url(str(sub2_1_path))
    sub2_1_url_path = Path(git_server.url_to_local_path(sub2_1_url))
    sub2_1_url_path.mkdir()
    run_git(sub2_1_url_path, "init", "--bare")
    run_git(full_sub2_path, "remote", "add", "origin", sub2_1_url)
    run_git(full_sub2_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    sub3_path = workspace_path
    sub3_1_path = Path("repo_3")
    os.mkdir(sub3_1_path)
    os.chdir(sub3_1_path)
    full_sub3_path: Path = Path(os.path.join(workspace_path, sub3_path, sub3_1_path))
    run_git(full_sub3_path, "init")
    sub3_1_1_file = Path("in_repo.txt")
    sub3_1_1_file.touch()
    run_git(full_sub3_path, "add", "in_repo.txt")
    run_git(full_sub3_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub3_1_url = git_server.get_url(str(sub3_1_path))
    sub3_1_url_path = Path(git_server.url_to_local_path(sub3_1_url))
    sub3_1_url_path.mkdir()
    run_git(sub3_1_url_path, "init", "--bare")
    run_git(full_sub3_path, "remote", "add", "origin", sub3_1_url)
    run_git(full_sub3_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    tsrc_cli.run("dump-manifest", "--raw", ".", "--save-to", "later_manifest.yml")

    """
    ====================================================
    now: let us create Workspace with Repos and Manifest
    """

    git_server.add_repo("repo_4")
    git_server.push_file("repo_4", "repo_4_file.txt")
    git_server.add_repo("repo_5")
    git_server.push_file("repo_5", "repo_5_file.txt")
    git_server.add_repo("repo_6")
    git_server.push_file("repo_6", "repo_6_file.txt")
    manifest_url = git_server.manifest_url

    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    git_server.add_group("group_4", ["manifest", "repo_4"])
    git_server.add_group("group_5", ["manifest", "repo_5"])
    git_server.add_group("group_6", ["manifest", "repo_6"])

    tsrc_cli.run(
        "init",
        "--branch",
        "master",
        manifest_url,
        "--group",
        "group_4",
        "group_5",
        "group_6",
    )
    tsrc_cli.run("sync")
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # move previous repos so we can determine if they were brought back again
    shutil.move(workspace_path / "repo_1", workspace_path / "__repo_1")
    shutil.move(workspace_path / "repo_2", workspace_path / "__repo_2")
    shutil.move(workspace_path / "repo_3", workspace_path / "__repo_3")

    """
    ==========
    now: introduce previous manifest
    """

    shutil.copyfile("later_manifest.yml", Path("manifest") / "manifest.yml")
    manifest_path = workspace_path / "manifest"

    # write 'groups' and 'switch' to manifest
    with open(manifest_path / "manifest.yml", "a") as fm_file:
        fm_file.write("groups:\n  group_all:\n    repos: [repo_1, repo_2]\n")
        fm_file.write("  group_a:\n    repos: [repo_1]\n")

    run_git(manifest_path, "checkout", "-b", "dev")
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "new version - dev")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # set to new manifest branch
    tsrc_cli.run("manifest", "--branch", "dev")

    # now with requrested Groups
    message_recorder.reset()
    tsrc_cli.run("status")

    message_recorder.reset()
    tsrc_cli.run("sync", "--switch", "--groups", "group_all")

    message_recorder.reset()
    tsrc_cli.run("status")

    assert message_recorder.find(r"\* repo_[1-2] master")
    assert not message_recorder.find(r"\* repo_[3-9]")


def test_sync__switch__cfg_groups__to__empty_group_m_switch(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Alias:

    Configured groups --> empty 'switch' groups config

    Conditions:

    * Workspace with configured groups
    * FM groups does not intersect
    * empty ([]) 'switch' configuration

    Outcome:

    * synced all repos as Workspace configuration should be reset
    which means Groups should be: '[]'
    """
    sub1_path = workspace_path
    sub1_1_path = Path("repo_1")
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)
    full_sub1_path: Path = Path(os.path.join(workspace_path, sub1_path, sub1_1_path))
    run_git(full_sub1_path, "init")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full_sub1_path, "add", "in_repo.txt")
    run_git(full_sub1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub1_1_url = git_server.get_url(str(sub1_1_path))
    sub1_1_url_path = Path(git_server.url_to_local_path(sub1_1_url))
    sub1_1_url_path.mkdir()
    run_git(sub1_1_url_path, "init", "--bare")
    run_git(full_sub1_path, "remote", "add", "origin", sub1_1_url)
    run_git(full_sub1_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    sub2_path = workspace_path
    sub2_1_path = Path("repo_2")
    os.mkdir(sub2_1_path)
    os.chdir(sub2_1_path)
    full_sub2_path: Path = Path(os.path.join(workspace_path, sub2_path, sub2_1_path))
    run_git(full_sub2_path, "init")
    sub2_1_1_file = Path("in_repo.txt")
    sub2_1_1_file.touch()
    run_git(full_sub2_path, "add", "in_repo.txt")
    run_git(full_sub2_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub2_1_url = git_server.get_url(str(sub2_1_path))
    sub2_1_url_path = Path(git_server.url_to_local_path(sub2_1_url))
    sub2_1_url_path.mkdir()
    run_git(sub2_1_url_path, "init", "--bare")
    run_git(full_sub2_path, "remote", "add", "origin", sub2_1_url)
    run_git(full_sub2_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    sub3_path = workspace_path
    sub3_1_path = Path("repo_3")
    os.mkdir(sub3_1_path)
    os.chdir(sub3_1_path)
    full_sub3_path: Path = Path(os.path.join(workspace_path, sub3_path, sub3_1_path))
    run_git(full_sub3_path, "init")
    sub3_1_1_file = Path("in_repo.txt")
    sub3_1_1_file.touch()
    run_git(full_sub3_path, "add", "in_repo.txt")
    run_git(full_sub3_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub3_1_url = git_server.get_url(str(sub3_1_path))
    sub3_1_url_path = Path(git_server.url_to_local_path(sub3_1_url))
    sub3_1_url_path.mkdir()
    run_git(sub3_1_url_path, "init", "--bare")
    run_git(full_sub3_path, "remote", "add", "origin", sub3_1_url)
    run_git(full_sub3_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    tsrc_cli.run("dump-manifest", "--raw", ".", "--save-to", "later_manifest.yml")

    """
    ====================================================
    now: let us create Workspace with Repos and Manifest
    """

    git_server.add_repo("repo_4")
    git_server.push_file("repo_4", "repo_4_file.txt")
    git_server.add_repo("repo_5")
    git_server.push_file("repo_5", "repo_5_file.txt")
    git_server.add_repo("repo_6")
    git_server.push_file("repo_6", "repo_6_file.txt")
    manifest_url = git_server.manifest_url

    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    git_server.add_group("group_4", ["manifest", "repo_4"])
    git_server.add_group("group_5", ["manifest", "repo_5"])
    git_server.add_group("group_6", ["manifest", "repo_6"])

    # git_server.manifest.configure_group("group_3", ["manifest", "repo_3"])

    tsrc_cli.run(
        "init",
        "--branch",
        "master",
        manifest_url,
        "--group",
        "group_4",
        "group_5",
        "group_6",
    )
    tsrc_cli.run("sync")
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # move previous repos so we can determine if they were brought back again
    shutil.move(workspace_path / "repo_1", workspace_path / "__repo_1")
    shutil.move(workspace_path / "repo_2", workspace_path / "__repo_2")
    shutil.move(workspace_path / "repo_3", workspace_path / "__repo_3")

    """
    ==========
    now: introduce previous manifest
    """

    shutil.copyfile("later_manifest.yml", Path("manifest") / "manifest.yml")
    manifest_path = workspace_path / "manifest"

    # write 'groups' and 'switch' to manifest
    with open(manifest_path / "manifest.yml", "a") as fm_file:
        fm_file.write("groups:\n  group_all:\n    repos: [repo_1, repo_2]\n")
        fm_file.write("  group_a:\n    repos: [repo_1]\n")
        fm_file.write("switch:\n  config:\n    groups: []\n")

    run_git(manifest_path, "checkout", "-b", "dev")
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "new version - dev")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # set to new manifest branch
    tsrc_cli.run("manifest", "--branch", "dev")

    # now with requrested Groups
    message_recorder.reset()
    tsrc_cli.run("status")

    message_recorder.reset()
    tsrc_cli.run("sync", "--switch")

    message_recorder.reset()
    tsrc_cli.run("status")

    assert message_recorder.find(r"\* repo_[1-3] master")
    assert not message_recorder.find(r"\* repo_[4-9]")


def test_sync__switch__cfg_groups__to__no_m_sw_cfg_groups(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Alias:

    Configured groups --> no manifest switch option

    Conditions:

    * Workspace with configured groups
    * FM does not contain any 'switch' part
    * FM groups does not intersect

    Outcome:

    * Workspace configuration of groups cleared
    """
    sub1_path = workspace_path
    sub1_1_path = Path("repo_1")
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)
    full_sub1_path: Path = Path(os.path.join(workspace_path, sub1_path, sub1_1_path))
    run_git(full_sub1_path, "init")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full_sub1_path, "add", "in_repo.txt")
    run_git(full_sub1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub1_1_url = git_server.get_url(str(sub1_1_path))
    sub1_1_url_path = Path(git_server.url_to_local_path(sub1_1_url))
    sub1_1_url_path.mkdir()
    run_git(sub1_1_url_path, "init", "--bare")
    run_git(full_sub1_path, "remote", "add", "origin", sub1_1_url)
    run_git(full_sub1_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    sub2_path = workspace_path
    sub2_1_path = Path("repo_2")
    os.mkdir(sub2_1_path)
    os.chdir(sub2_1_path)
    full_sub2_path: Path = Path(os.path.join(workspace_path, sub2_path, sub2_1_path))
    run_git(full_sub2_path, "init")
    sub2_1_1_file = Path("in_repo.txt")
    sub2_1_1_file.touch()
    run_git(full_sub2_path, "add", "in_repo.txt")
    run_git(full_sub2_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub2_1_url = git_server.get_url(str(sub2_1_path))
    sub2_1_url_path = Path(git_server.url_to_local_path(sub2_1_url))
    sub2_1_url_path.mkdir()
    run_git(sub2_1_url_path, "init", "--bare")
    run_git(full_sub2_path, "remote", "add", "origin", sub2_1_url)
    run_git(full_sub2_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    sub3_path = workspace_path
    sub3_1_path = Path("repo_3")
    os.mkdir(sub3_1_path)
    os.chdir(sub3_1_path)
    full_sub3_path: Path = Path(os.path.join(workspace_path, sub3_path, sub3_1_path))
    run_git(full_sub3_path, "init")
    sub3_1_1_file = Path("in_repo.txt")
    sub3_1_1_file.touch()
    run_git(full_sub3_path, "add", "in_repo.txt")
    run_git(full_sub3_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub3_1_url = git_server.get_url(str(sub3_1_path))
    sub3_1_url_path = Path(git_server.url_to_local_path(sub3_1_url))
    sub3_1_url_path.mkdir()
    run_git(sub3_1_url_path, "init", "--bare")
    run_git(full_sub3_path, "remote", "add", "origin", sub3_1_url)
    run_git(full_sub3_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    tsrc_cli.run("dump-manifest", "--raw", ".", "--save-to", "later_manifest.yml")

    """
    ====================================================
    now: let us create Workspace with Repos and Manifest
    """

    git_server.add_repo("repo_4")
    git_server.push_file("repo_4", "repo_4_file.txt")
    git_server.add_repo("repo_5")
    git_server.push_file("repo_5", "repo_5_file.txt")
    git_server.add_repo("repo_6")
    git_server.push_file("repo_6", "repo_6_file.txt")
    manifest_url = git_server.manifest_url

    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    git_server.add_group("group_4", ["manifest", "repo_4"])
    git_server.add_group("group_5", ["manifest", "repo_5"])
    git_server.add_group("group_6", ["manifest", "repo_6"])

    # git_server.manifest.configure_group("group_3", ["manifest", "repo_3"])

    tsrc_cli.run(
        "init",
        "--branch",
        "master",
        manifest_url,
        "--group",
        "group_4",
        "group_5",
        "group_6",
    )
    tsrc_cli.run("sync")
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # move previous repos so we can determine if they were brought back again
    shutil.move(workspace_path / "repo_1", workspace_path / "__repo_1")
    shutil.move(workspace_path / "repo_2", workspace_path / "__repo_2")
    shutil.move(workspace_path / "repo_3", workspace_path / "__repo_3")

    """
    ==========
    now: introduce previous manifest
    """

    shutil.copyfile("later_manifest.yml", Path("manifest") / "manifest.yml")
    manifest_path = workspace_path / "manifest"

    # write 'groups' and 'switch' to manifest
    with open(manifest_path / "manifest.yml", "a") as fm_file:
        fm_file.write("groups:\n  group_all:\n    repos: [repo_1, repo_2]\n")
        fm_file.write("  group_a:\n    repos: [repo_1]\n")

    run_git(manifest_path, "checkout", "-b", "dev")
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "new version - dev")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # set to new manifest branch
    tsrc_cli.run("manifest", "--branch", "dev")

    tsrc_cli.run("status")

    message_recorder.reset()
    tsrc_cli.run("sync", "--switch")

    # we are not updating 'repos_groups' (Groups configuration) even when on
    # '--switch' due to there is no change from '[]' to '[]'
    assert message_recorder.find(
        r"=> No Manifest's switch configuration found, using default configuration"
    )
    assert message_recorder.find(r"=> Updating Workspace Groups configuration")
    assert not message_recorder.find(
        r"=> Leaving Workspace Groups configuration intact"
    )

    message_recorder.reset()
    tsrc_cli.run("status")

    assert message_recorder.find(r"\* repo_[1-3] master")
    assert not message_recorder.find(r"\* repo_[4-9]")


def test_sync__switch__not_cfg_groups__to__m_sw_cfg_groups__with_cmd_groups(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Alias:

    NOT configured groups --> manifest (switch option) configured groups
    while using only selected group

    Conditions:

    * Workspace without configured Groups
    * FM contains Groups and correct 'switch' part
    * using 'sync' with '--groups' to select only one group

    Outcome:

    * synced to manifest to selected group (as it match switch configuration)
    * workspace config updated according to selected group
    """

    sub1_path = workspace_path
    sub1_1_path = Path("repo_1")
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)
    full_sub1_path: Path = Path(os.path.join(workspace_path, sub1_path, sub1_1_path))
    run_git(full_sub1_path, "init")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full_sub1_path, "add", "in_repo.txt")
    run_git(full_sub1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub1_1_url = git_server.get_url(str(sub1_1_path))
    sub1_1_url_path = Path(git_server.url_to_local_path(sub1_1_url))
    sub1_1_url_path.mkdir()
    run_git(sub1_1_url_path, "init", "--bare")
    run_git(full_sub1_path, "remote", "add", "origin", sub1_1_url)
    run_git(full_sub1_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    sub2_path = workspace_path
    sub2_1_path = Path("repo_2")
    os.mkdir(sub2_1_path)
    os.chdir(sub2_1_path)
    full_sub2_path: Path = Path(os.path.join(workspace_path, sub2_path, sub2_1_path))
    run_git(full_sub2_path, "init")
    sub2_1_1_file = Path("in_repo.txt")
    sub2_1_1_file.touch()
    run_git(full_sub2_path, "add", "in_repo.txt")
    run_git(full_sub2_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub2_1_url = git_server.get_url(str(sub2_1_path))
    sub2_1_url_path = Path(git_server.url_to_local_path(sub2_1_url))
    sub2_1_url_path.mkdir()
    run_git(sub2_1_url_path, "init", "--bare")
    run_git(full_sub2_path, "remote", "add", "origin", sub2_1_url)
    run_git(full_sub2_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    sub3_path = workspace_path
    sub3_1_path = Path("repo_3")
    os.mkdir(sub3_1_path)
    os.chdir(sub3_1_path)
    full_sub3_path: Path = Path(os.path.join(workspace_path, sub3_path, sub3_1_path))
    run_git(full_sub3_path, "init")
    sub3_1_1_file = Path("in_repo.txt")
    sub3_1_1_file.touch()
    run_git(full_sub3_path, "add", "in_repo.txt")
    run_git(full_sub3_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub3_1_url = git_server.get_url(str(sub3_1_path))
    sub3_1_url_path = Path(git_server.url_to_local_path(sub3_1_url))
    sub3_1_url_path.mkdir()
    run_git(sub3_1_url_path, "init", "--bare")
    run_git(full_sub3_path, "remote", "add", "origin", sub3_1_url)
    run_git(full_sub3_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    tsrc_cli.run("dump-manifest", "--raw", ".", "--save-to", "later_manifest.yml")

    """
    ====================================================
    now: let us create Workspace with Repos and Manifest
    """

    git_server.add_repo("repo_4")
    git_server.push_file("repo_4", "repo_4_file.txt")
    git_server.add_repo("repo_5")
    git_server.push_file("repo_5", "repo_5_file.txt")
    git_server.add_repo("repo_6")
    git_server.push_file("repo_6", "repo_6_file.txt")
    manifest_url = git_server.manifest_url

    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    tsrc_cli.run(
        "init",
        "--branch",
        "master",
        manifest_url,
    )
    tsrc_cli.run("sync")
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # move previous repos so we can determine if they were brought back again
    shutil.move(workspace_path / "repo_1", workspace_path / "__repo_1")
    shutil.move(workspace_path / "repo_2", workspace_path / "__repo_2")
    shutil.move(workspace_path / "repo_3", workspace_path / "__repo_3")

    """
    ==========
    now: introduce previous manifest
    """

    shutil.copyfile("later_manifest.yml", Path("manifest") / "manifest.yml")
    manifest_path = workspace_path / "manifest"

    # write 'groups' and 'switch' to manifest
    with open(manifest_path / "manifest.yml", "a") as fm_file:
        fm_file.write("groups:\n  group_all:\n    repos: [repo_1, repo_2]\n")
        fm_file.write("  group_a:\n    repos: [repo_1]\n")
        fm_file.write("  group_b:\n    repos: [repo_2]\n")
        fm_file.write("switch:\n  config:\n    groups:\n      - group_a\n")
        fm_file.write("      - group_b\n")

    run_git(manifest_path, "checkout", "-b", "dev")
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "group_a and group_b")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # set to new manifest branch
    tsrc_cli.run("manifest", "--branch", "dev")

    # now with requrested Groups
    message_recorder.reset()
    tsrc_cli.run("status")

    message_recorder.reset()
    tsrc_cli.run("sync", "--switch", "--group", "group_b")

    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* repo_2 master")
    assert not message_recorder.find(r"\* repo_1")
    assert not message_recorder.find(r"\* repo_[3-9]")


def test_sync__switch__not_cfg_groups__to__m_sw_cfg_groups(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Alias:

    NOT configured groups --> manifest (switch option) configured groups

    Conditions:

    * Workspace without configured Groups
    * FM contains Groups and correct 'switch' part

    Outcome:

    * synced to manifest configured groups
    * workspace config updated according to manifest switch part
    """

    sub1_path = workspace_path
    sub1_1_path = Path("repo_1")
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)
    full_sub1_path: Path = Path(os.path.join(workspace_path, sub1_path, sub1_1_path))
    run_git(full_sub1_path, "init")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full_sub1_path, "add", "in_repo.txt")
    run_git(full_sub1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub1_1_url = git_server.get_url(str(sub1_1_path))
    sub1_1_url_path = Path(git_server.url_to_local_path(sub1_1_url))
    sub1_1_url_path.mkdir()
    run_git(sub1_1_url_path, "init", "--bare")
    run_git(full_sub1_path, "remote", "add", "origin", sub1_1_url)
    run_git(full_sub1_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    sub2_path = workspace_path
    sub2_1_path = Path("repo_2")
    os.mkdir(sub2_1_path)
    os.chdir(sub2_1_path)
    full_sub2_path: Path = Path(os.path.join(workspace_path, sub2_path, sub2_1_path))
    run_git(full_sub2_path, "init")
    sub2_1_1_file = Path("in_repo.txt")
    sub2_1_1_file.touch()
    run_git(full_sub2_path, "add", "in_repo.txt")
    run_git(full_sub2_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub2_1_url = git_server.get_url(str(sub2_1_path))
    sub2_1_url_path = Path(git_server.url_to_local_path(sub2_1_url))
    sub2_1_url_path.mkdir()
    run_git(sub2_1_url_path, "init", "--bare")
    run_git(full_sub2_path, "remote", "add", "origin", sub2_1_url)
    run_git(full_sub2_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    sub3_path = workspace_path
    sub3_1_path = Path("repo_3")
    os.mkdir(sub3_1_path)
    os.chdir(sub3_1_path)
    full_sub3_path: Path = Path(os.path.join(workspace_path, sub3_path, sub3_1_path))
    run_git(full_sub3_path, "init")
    sub3_1_1_file = Path("in_repo.txt")
    sub3_1_1_file.touch()
    run_git(full_sub3_path, "add", "in_repo.txt")
    run_git(full_sub3_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub3_1_url = git_server.get_url(str(sub3_1_path))
    sub3_1_url_path = Path(git_server.url_to_local_path(sub3_1_url))
    sub3_1_url_path.mkdir()
    run_git(sub3_1_url_path, "init", "--bare")
    run_git(full_sub3_path, "remote", "add", "origin", sub3_1_url)
    run_git(full_sub3_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    tsrc_cli.run("dump-manifest", "--raw", ".", "--save-to", "later_manifest.yml")

    """
    ====================================================
    now: let us create Workspace with Repos and Manifest
    """

    git_server.add_repo("repo_4")
    git_server.push_file("repo_4", "repo_4_file.txt")
    git_server.add_repo("repo_5")
    git_server.push_file("repo_5", "repo_5_file.txt")
    git_server.add_repo("repo_6")
    git_server.push_file("repo_6", "repo_6_file.txt")
    manifest_url = git_server.manifest_url

    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    tsrc_cli.run(
        "init",
        "--branch",
        "master",
        manifest_url,
    )
    tsrc_cli.run("sync")
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # move previous repos so we can determine if they were brought back again
    shutil.move(workspace_path / "repo_1", workspace_path / "__repo_1")
    shutil.move(workspace_path / "repo_2", workspace_path / "__repo_2")
    shutil.move(workspace_path / "repo_3", workspace_path / "__repo_3")

    """
    ==========
    now: introduce previous manifest
    """

    shutil.copyfile("later_manifest.yml", Path("manifest") / "manifest.yml")
    manifest_path = workspace_path / "manifest"

    # write 'groups' and 'switch' to manifest
    with open(manifest_path / "manifest.yml", "a") as fm_file:
        fm_file.write("groups:\n  group_all:\n    repos: [repo_1, repo_2]\n")
        fm_file.write("  group_a:\n    repos: [repo_1]\n")
        fm_file.write("switch:\n  config:\n    groups:\n      - group_a")

    run_git(manifest_path, "checkout", "-b", "dev")
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "new version - dev")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # set to new manifest branch
    tsrc_cli.run("manifest", "--branch", "dev")

    # now with requrested Groups
    message_recorder.reset()
    tsrc_cli.run("status")

    message_recorder.reset()
    tsrc_cli.run("sync", "--switch")

    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* repo_1 master")
    assert not message_recorder.find(r"\* repo_[2-9]")


@pytest.mark.last
def test_sync__switch__cfg_groups__to__m_sw_cfg_groups__with_cmd_groups(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Alias:

    configured groups --> manifest (switch option) configured groups :: with cmd groups

    -------
    CASE 1: no match

    Conditions:

    * groups are configured in Workspace
    * FM contains different groups
    * FM contains 'switch' part with properly set one group 'group_a'
    that does not match anywhere
    * along with '--switch', the '--group group_b' is requested

    Outcome:

    * 'group_a' and 'group_b' does not have intersection, thus nothing
    is synced, the 'sync' is ignored, Error message is printed

    -------
    CASE 2: match different group (not from 'swtich'):

    * let us update 'switch' configuration with 'group_all', commit, push

    Situation:

    * now STILL!!! 'group_a' + 'group_all' does not have intersection with
    'group_b', however all items of 'group_b' ('repo_2') is covered by
    'group_all'. and it this case we can allow to set 'group_b', due to
    it is fully covered in 'switch' configuration

    Outcome:

    * Workspace gets synced to 'group_b' successfully, config is also updated
    """

    sub1_path = workspace_path
    sub1_1_path = Path("repo_1")
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)
    full_sub1_path: Path = Path(os.path.join(workspace_path, sub1_path, sub1_1_path))
    run_git(full_sub1_path, "init")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full_sub1_path, "add", "in_repo.txt")
    run_git(full_sub1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub1_1_url = git_server.get_url(str(sub1_1_path))
    sub1_1_url_path = Path(git_server.url_to_local_path(sub1_1_url))
    sub1_1_url_path.mkdir()
    run_git(sub1_1_url_path, "init", "--bare")
    run_git(full_sub1_path, "remote", "add", "origin", sub1_1_url)
    run_git(full_sub1_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    sub2_path = workspace_path
    sub2_1_path = Path("repo_2")
    os.mkdir(sub2_1_path)
    os.chdir(sub2_1_path)
    full_sub2_path: Path = Path(os.path.join(workspace_path, sub2_path, sub2_1_path))
    run_git(full_sub2_path, "init")
    sub2_1_1_file = Path("in_repo.txt")
    sub2_1_1_file.touch()
    run_git(full_sub2_path, "add", "in_repo.txt")
    run_git(full_sub2_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub2_1_url = git_server.get_url(str(sub2_1_path))
    sub2_1_url_path = Path(git_server.url_to_local_path(sub2_1_url))
    sub2_1_url_path.mkdir()
    run_git(sub2_1_url_path, "init", "--bare")
    run_git(full_sub2_path, "remote", "add", "origin", sub2_1_url)
    run_git(full_sub2_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    sub3_path = workspace_path
    sub3_1_path = Path("repo_3")
    os.mkdir(sub3_1_path)
    os.chdir(sub3_1_path)
    full_sub3_path: Path = Path(os.path.join(workspace_path, sub3_path, sub3_1_path))
    run_git(full_sub3_path, "init")
    sub3_1_1_file = Path("in_repo.txt")
    sub3_1_1_file.touch()
    run_git(full_sub3_path, "add", "in_repo.txt")
    run_git(full_sub3_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub3_1_url = git_server.get_url(str(sub3_1_path))
    sub3_1_url_path = Path(git_server.url_to_local_path(sub3_1_url))
    sub3_1_url_path.mkdir()
    run_git(sub3_1_url_path, "init", "--bare")
    run_git(full_sub3_path, "remote", "add", "origin", sub3_1_url)
    run_git(full_sub3_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    tsrc_cli.run("dump-manifest", "--raw", ".", "--save-to", "later_manifest.yml")

    """
    ====================================================
    now: let us create Workspace with Repos and Manifest
    """

    git_server.add_repo("repo_4")
    git_server.push_file("repo_4", "repo_4_file.txt")
    git_server.add_repo("repo_5")
    git_server.push_file("repo_5", "repo_5_file.txt")
    git_server.add_repo("repo_6")
    git_server.push_file("repo_6", "repo_6_file.txt")
    manifest_url = git_server.manifest_url

    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    git_server.add_group("group_4", ["manifest", "repo_4"])
    git_server.add_group("group_5", ["manifest", "repo_5"])
    git_server.add_group("group_6", ["manifest", "repo_6"])

    # git_server.manifest.configure_group("group_3", ["manifest", "repo_3"])

    tsrc_cli.run(
        "init",
        "--branch",
        "master",
        manifest_url,
        "--group",
        "group_4",
        "group_5",
        "group_6",
    )
    tsrc_cli.run("sync")
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # move previous repos so we can determine if they were brought back again
    shutil.move(workspace_path / "repo_1", workspace_path / "__repo_1")
    shutil.move(workspace_path / "repo_2", workspace_path / "__repo_2")
    shutil.move(workspace_path / "repo_3", workspace_path / "__repo_3")

    """
    ==========
    now: introduce previous manifest
    """

    shutil.copyfile("later_manifest.yml", Path("manifest") / "manifest.yml")
    manifest_path = workspace_path / "manifest"

    # - CASE 1: --------------------------------------------
    # set 'swtich' configuration only to contain 'group_a'
    # while we want only 'group_be'. here 'group_a' and 'group_b'
    # does not have (full) intersection, therefore there is
    # no match and Error is printed

    # write 'groups' and 'switch' to manifest
    with open(manifest_path / "manifest.yml", "a") as fm_file:
        fm_file.write("groups:\n  group_all:\n    repos: [repo_1, repo_2]\n")
        fm_file.write("  group_a:\n    repos: [repo_1]\n")
        fm_file.write("  group_b:\n    repos: [repo_2]\n")
        fm_file.write("switch:\n  config:\n    groups:\n      - group_a\n")

    run_git(manifest_path, "checkout", "-b", "dev")
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "case 1: no match, error")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # set to new manifest branch
    tsrc_cli.run("manifest", "--branch", "dev")

    # here: 'group_a' does not have intersection with its Repos
    #   to 'group_b', therefore no match has to be reported

    message_recorder.reset()
    tsrc_cli.run("sync", "--switch", "--groups", "group_b")
    assert message_recorder.find(
        r"Error: Provided Groups does not match any in the Manifest"
    )

    # - CASE 2: ---------------------------------------------
    # now another case of the same, but here the 'switch'
    # groups can fully cover Repos (items) of 'group_b'
    # due to 'group_a' and 'group_all' cover 'repo2' as it is
    # in 'group_all'. so we cal clrearly set 'group_b' fully

    with open(manifest_path / "manifest.yml", "a") as fm_file:
        fm_file.write("      - group_all")

    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "case 2: match group not in switch cfg")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    tsrc_cli.run("sync", "--switch")
    tsrc_cli.run("manifest", "--branch", "master")
    tsrc_cli.run("sync", "--switch")
    tsrc_cli.run("manifest", "--branch", "dev")

    # it should be accepted correctly even if 'group_b'
    #   is not found in 'switch' section
    message_recorder.reset()
    tsrc_cli.run("sync", "--switch", "--groups", "group_b")
    assert message_recorder.find(r"=> Using Manifest's switch configuration")
    assert message_recorder.find(r"=> Updating Workspace Groups configuration")

    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* repo_2 master")
    assert not message_recorder.find(r"\* repo_[3-9]")
    assert not message_recorder.find(r"\* repo_1")

    # test config as well
    is_ok_count: int = 0
    with open(Path(".tsrc") / "config.yml", "r") as cfgf:
        # this_config_lines = cfgf.readlines()
        this_config_lines = cfgf.read()
        if "group_b" in this_config_lines:
            is_ok_count += 1  # must insist on Error
        elif "group_" in this_config_lines:  # any other group
            is_ok_count -= 2

    if is_ok_count != 1:
        raise AssertionError("config contains wrong groups")


def test_sync__switch__cfg_groups__to__m_sw_cfg_groups(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Alias:

    configured groups --> manifest (switch option) configured groups

    Conditions:

    * groups are configured in Workspace
    * FM contains different groups
    * FM contains 'switch' part with properly set one group 'group_a'
    that does not match anywhere

    Outcome:

    * synced to group: 'group_a'
    * workspace config updated to 'group_a' only
    """

    sub1_path = workspace_path
    sub1_1_path = Path("repo_1")
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)
    full_sub1_path: Path = Path(os.path.join(workspace_path, sub1_path, sub1_1_path))
    run_git(full_sub1_path, "init")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full_sub1_path, "add", "in_repo.txt")
    run_git(full_sub1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub1_1_url = git_server.get_url(str(sub1_1_path))
    sub1_1_url_path = Path(git_server.url_to_local_path(sub1_1_url))
    sub1_1_url_path.mkdir()
    run_git(sub1_1_url_path, "init", "--bare")
    run_git(full_sub1_path, "remote", "add", "origin", sub1_1_url)
    run_git(full_sub1_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    sub2_path = workspace_path
    sub2_1_path = Path("repo_2")
    os.mkdir(sub2_1_path)
    os.chdir(sub2_1_path)
    full_sub2_path: Path = Path(os.path.join(workspace_path, sub2_path, sub2_1_path))
    run_git(full_sub2_path, "init")
    sub2_1_1_file = Path("in_repo.txt")
    sub2_1_1_file.touch()
    run_git(full_sub2_path, "add", "in_repo.txt")
    run_git(full_sub2_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub2_1_url = git_server.get_url(str(sub2_1_path))
    sub2_1_url_path = Path(git_server.url_to_local_path(sub2_1_url))
    sub2_1_url_path.mkdir()
    run_git(sub2_1_url_path, "init", "--bare")
    run_git(full_sub2_path, "remote", "add", "origin", sub2_1_url)
    run_git(full_sub2_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    sub3_path = workspace_path
    sub3_1_path = Path("repo_3")
    os.mkdir(sub3_1_path)
    os.chdir(sub3_1_path)
    full_sub3_path: Path = Path(os.path.join(workspace_path, sub3_path, sub3_1_path))
    run_git(full_sub3_path, "init")
    sub3_1_1_file = Path("in_repo.txt")
    sub3_1_1_file.touch()
    run_git(full_sub3_path, "add", "in_repo.txt")
    run_git(full_sub3_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # take care of remote
    sub3_1_url = git_server.get_url(str(sub3_1_path))
    sub3_1_url_path = Path(git_server.url_to_local_path(sub3_1_url))
    sub3_1_url_path.mkdir()
    run_git(sub3_1_url_path, "init", "--bare")
    run_git(full_sub3_path, "remote", "add", "origin", sub3_1_url)
    run_git(full_sub3_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    tsrc_cli.run("dump-manifest", "--raw", ".", "--save-to", "later_manifest.yml")

    """
    ====================================================
    now: let us create Workspace with Repos and Manifest
    """

    git_server.add_repo("repo_4")
    git_server.push_file("repo_4", "repo_4_file.txt")
    git_server.add_repo("repo_5")
    git_server.push_file("repo_5", "repo_5_file.txt")
    git_server.add_repo("repo_6")
    git_server.push_file("repo_6", "repo_6_file.txt")
    manifest_url = git_server.manifest_url

    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    git_server.add_group("group_4", ["manifest", "repo_4"])
    git_server.add_group("group_5", ["manifest", "repo_5"])
    git_server.add_group("group_6", ["manifest", "repo_6"])

    # git_server.manifest.configure_group("group_3", ["manifest", "repo_3"])

    tsrc_cli.run(
        "init",
        "--branch",
        "master",
        manifest_url,
        "--group",
        "group_4",
        "group_5",
        "group_6",
    )
    tsrc_cli.run("sync")
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # move previous repos so we can determine if they were brought back again
    shutil.move(workspace_path / "repo_1", workspace_path / "__repo_1")
    shutil.move(workspace_path / "repo_2", workspace_path / "__repo_2")
    shutil.move(workspace_path / "repo_3", workspace_path / "__repo_3")

    """
    ==========
    now: introduce previous manifest
    """

    shutil.copyfile("later_manifest.yml", Path("manifest") / "manifest.yml")
    manifest_path = workspace_path / "manifest"

    # write 'groups' and 'switch' to manifest
    with open(manifest_path / "manifest.yml", "a") as fm_file:
        fm_file.write("groups:\n  group_all:\n    repos: [repo_1, repo_2]\n")
        fm_file.write("  group_a:\n    repos: [repo_1]\n")
        fm_file.write("switch:\n  config:\n    groups:\n      - group_a")

    run_git(manifest_path, "checkout", "-b", "dev")
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "new version - dev")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # set to new manifest branch
    tsrc_cli.run("manifest", "--branch", "dev")

    # now with requrested Groups
    message_recorder.reset()
    tsrc_cli.run("status")

    message_recorder.reset()
    tsrc_cli.run("sync", "--switch")

    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* repo_1 master")
    assert not message_recorder.find(r"\* repo_[2-9]")
