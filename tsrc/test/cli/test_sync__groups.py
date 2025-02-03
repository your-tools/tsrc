"""
test how 'sync' should work when using Groups.
Try out different scenarios
"""

import os
import shutil
from pathlib import Path

# import pytest
from cli_ui.tests import MessageRecorder

from tsrc.git import run_git
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer
from tsrc.workspace_config import WorkspaceConfig


def test_sync__group(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    General purpos test.
    Use it as a base for specific tests
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

    tsrc_cli.run("dump-manifest", "--raw", ".", "--save-to", "later_manifest.yml")

    """
    ====================================================
    now: let us create Workspace with Repos and Manifest
    """

    git_server.add_repo("repo_3")
    git_server.push_file("repo_3", "repo_3_file.txt")
    git_server.add_repo("repo_4")
    git_server.push_file("repo_4", "repo_4_file.txt")
    git_server.add_repo("repo_5")
    git_server.push_file("repo_5", "repo_5_file.txt")
    manifest_url = git_server.manifest_url

    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    git_server.add_group("group_3", ["manifest", "repo_3"])
    git_server.add_group("group_4", ["manifest", "repo_4"])
    git_server.add_group("group_5", ["manifest", "repo_5"])

    # git_server.manifest.configure_group("group_3", ["manifest", "repo_3"])

    tsrc_cli.run("init", "--branch", "master", manifest_url)
    tsrc_cli.run("sync")
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # move previous repos so we can determine if they ware brought back again
    shutil.move(workspace_path / "repo_1", workspace_path / "__repo_1")

    """
    ==========
    now: introduce previous manifest
    """

    shutil.copyfile("later_manifest.yml", Path("manifest") / "manifest.yml")
    manifest_path = workspace_path / "manifest"

    # write groups to manifest
    with open(manifest_path / "manifest.yml", "a") as dm_file:
        dm_file.write("groups:\n  group_all:\n    repos: [repo_1, repo_2]\n")

    run_git(manifest_path, "checkout", "-b", "dev")
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "new version - dev")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # set to new manifest branch
    tsrc_cli.run("manifest", "--branch", "dev")

    # TODO: do not include this generic test in release


def test_sync__group__respect_cmd_line_group_options(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Verify if Groups entered on 'sync' command are respected when:
    * there are configured Groups,
    * curently configured Groups does not match any of Future Manifest
    * updating config is allowed
    * 'sync' only 1 out-of 2 Groups
    * thus configuration should contain only 1 Group (verify)

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

    tsrc_cli.run("dump-manifest", "--raw", ".", "--save-to", "later_manifest.yml")

    """
    ====================================================
    now: let us create Workspace with Repos and Manifest
    """

    git_server.add_repo("repo_3")
    git_server.push_file("repo_3", "repo_3_file.txt")
    git_server.add_repo("repo_4")
    git_server.push_file("repo_4", "repo_4_file.txt")
    git_server.add_repo("repo_5")
    git_server.push_file("repo_5", "repo_5_file.txt")
    manifest_url = git_server.manifest_url

    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    git_server.add_group("group_3", ["manifest", "repo_3"])
    git_server.add_group("group_4", ["manifest", "repo_4"])
    git_server.add_group("group_5", ["manifest", "repo_5"])

    # git_server.manifest.configure_group("group_3", ["manifest", "repo_3"])

    tsrc_cli.run("init", "--branch", "master", manifest_url)
    tsrc_cli.run("sync")
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # move previous repos so we can determine if they ware brought back again
    shutil.move(workspace_path / "repo_1", workspace_path / "__repo_1")
    shutil.move(workspace_path / "repo_2", workspace_path / "__repo_2")

    """
    ==========
    now: introduce previous manifest
    """

    shutil.copyfile("later_manifest.yml", Path("manifest") / "manifest.yml")
    manifest_path = workspace_path / "manifest"

    # write groups to manifest
    with open(manifest_path / "manifest.yml", "a") as dm_file:
        dm_file.write(
            "groups:\n  group_1:\n    repos: [repo_1]\n  group_2:\n    repos: [repo_2]"
        )

    run_git(manifest_path, "checkout", "-b", "dev")
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "new version - dev")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # set to new manifest branch
    tsrc_cli.run("manifest", "--branch", "dev")

    # sync selecting on 1 out of 2 Group
    message_recorder.reset()
    tsrc_cli.run("sync", "--groups", "group_1")
    assert message_recorder.find(r"=> Updating Workspace Groups configuration")

    # test how does 'config.yml' ends up
    is_ok_count: int = 0
    with open(Path(".tsrc") / "config.yml", "r") as cfgf:
        # this_config_lines = cfgf.readlines()
        this_config_lines = cfgf.read()
        if "group_2" in this_config_lines:
            is_ok_count -= 1  # must insist on Error
        if "group_1" in this_config_lines:
            is_ok_count += 2

    if is_ok_count != 2:
        raise AssertionError("config contains wrong groups")


def test_sync__group__fm_groups_not_in_config(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Situation:

    * configured Groups [group_3, group_4, group_5]
    * does not match any from Future Manifest's Groups
    * switching Manifest branch (to hit such case)
    * sync (without any Groups)

    Consequences:

    * configured Groups gets updated to: []
    * all FM repositories will gets synchronized therefore
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

    tsrc_cli.run("dump-manifest", "--raw", ".", "--save-to", "later_manifest.yml")

    """
    ====================================================
    now: let us create Workspace with Repos and Manifest
    """

    git_server.add_repo("repo_3")
    git_server.push_file("repo_3", "repo_3_file.txt")
    git_server.add_repo("repo_4")
    git_server.push_file("repo_4", "repo_4_file.txt")
    git_server.add_repo("repo_5")
    git_server.push_file("repo_5", "repo_5_file.txt")
    manifest_url = git_server.manifest_url

    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    git_server.add_group("group_3", ["manifest", "repo_3"])
    git_server.add_group("group_4", ["manifest", "repo_4"])
    git_server.add_group("group_5", ["manifest", "repo_5"])

    # git_server.manifest.configure_group("group_3", ["manifest", "repo_3"])

    # tsrc_cli.run("init", "--branch", "master", manifest_url)
    tsrc_cli.run(
        "init",
        "--branch",
        "master",
        manifest_url,
        "--group",
        "group_3",
        "group_4",
        "group_5",
    )
    tsrc_cli.run("sync")
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # move previous repos so we can determine if they ware brought back again
    shutil.move(workspace_path / "repo_1", workspace_path / "__repo_1")

    """
    ==========
    now: introduce previous manifest
    """

    shutil.copyfile("later_manifest.yml", Path("manifest") / "manifest.yml")
    manifest_path = workspace_path / "manifest"

    # write groups to manifest
    with open(manifest_path / "manifest.yml", "a") as dm_file:
        dm_file.write("groups:\n  group_all:\n    repos: [repo_1, repo_2]\n")

    run_git(manifest_path, "checkout", "-b", "dev")
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "new version - dev")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # set to new manifest branch
    tsrc_cli.run("manifest", "--branch", "dev")

    # should display all Groups from config + DM Groups + FM Groups
    message_recorder.reset()
    tsrc_cli.run("status")

    assert message_recorder.find(r"=> Destination \(Future Manifest description\)")
    assert message_recorder.find(
        r"\* manifest \(        << dev \) \(expected: master\) ~~ MANIFEST"
    )
    assert message_recorder.find(r"\* repo_3   \(        << master \)")
    assert message_recorder.find(r"\* repo_4   \(        << master \)")
    assert message_recorder.find(r"\* repo_5   \(        << master \)")
    assert message_recorder.find(r"- repo_1   \( master << ::: \)")
    assert message_recorder.find(r"\+ repo_2   \( master == master \)")

    message_recorder.reset()
    tsrc_cli.run("sync")
    assert message_recorder.find(r"=> Updating Workspace Groups configuration")

    # test how does 'config.yml' ends up
    with open(Path(".tsrc") / "config.yml", "r") as cfgf:
        this_config_lines = cfgf.read()
        if (
            "group_3" in this_config_lines
            or "group_4" in this_config_lines  # noqa: 503
            or "group_5" in this_config_lines  # noqa: 503
            or "group_all" in this_config_lines  # noqa: 503
        ):
            raise AssertionError("config contains wrong groups")

    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"=> Before possible GIT statuses, Workspace reports:")
    assert message_recorder.find(r"=> Destination")
    assert not message_recorder.find(r"=> Destination ")
    assert message_recorder.find(r"\* repo_1 master")
    assert message_recorder.find(r"\* repo_2 master")


def test_sync__group__dm_group_found_but_no_item_intersection_with_workspace(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Test corner cases when changing Manifest branch and 'sync'

    Situation:

    * configured Groups: ['group_3', 'group_4', 'group_5']
    * FM is with overlaping Group: 'group_3', but with different Repo (as item)
    * FM has also 'group_all' covering all new Repos
    * set new Manifest branch
    * sync only Group 'group_3'

    Consequences:

    * While FM has Group ('group_all') that covers all Repos, such Group is not configured.
    Only 'group_3', therefore
    * Configured Groups changes to only 'group_3'
    * BUT!!! as 'tsrc status' predicst FM only when no Groups are filtered-out, thus
    it shows that 2 Repos will be synced instead of 1, which is ok.
    (currently there is no way how to tell 'status' what Groups we would like to syncing,
    thus calculation of FM Repos can only be without filtering-out Groups)
    * when DM (finaly) does have overlaping Group ('group_3') with Repo that is not in the
    Workspace, DM Repo will be displayed as DM leftover.

    Conclusion:

    This behavior seems correct, but without way to reset Groups, we are calling for
    future troubles when Groups may overlap and when at least one match, Groups will
    be configured with match. '--no-update-config' will not help as old Groups may
    cause even more harm.
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

    tsrc_cli.run("dump-manifest", "--raw", ".", "--save-to", "later_manifest.yml")

    """
    ====================================================
    now: let us create Workspace with Repos and Manifest
    """

    git_server.add_repo("repo_3")
    git_server.push_file("repo_3", "repo_3_file.txt")
    git_server.add_repo("repo_4")
    git_server.push_file("repo_4", "repo_4_file.txt")
    git_server.add_repo("repo_5")
    git_server.push_file("repo_5", "repo_5_file.txt")
    manifest_url = git_server.manifest_url

    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    git_server.add_group("group_3", ["manifest", "repo_3"])
    git_server.add_group("group_4", ["manifest", "repo_4"])
    git_server.add_group("group_5", ["manifest", "repo_5"])

    # git_server.manifest.configure_group("group_3", ["manifest", "repo_3"])

    tsrc_cli.run(
        "init",
        "--branch",
        "master",
        manifest_url,
        "--group",
        "group_3",
        "group_4",
        "group_5",
    )
    tsrc_cli.run("sync")
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # move previous repos so we can determine if they ware brought back again
    shutil.move(workspace_path / "repo_1", workspace_path / "__repo_1")

    """
    ==========
    now: introduce previous manifest
    """

    shutil.copyfile("later_manifest.yml", Path("manifest") / "manifest.yml")
    manifest_path = workspace_path / "manifest"

    # write groups to manifest
    with open(manifest_path / "manifest.yml", "a") as fm_file:
        fm_file.write("groups:\n  group_all:\n    repos: [repo_1, repo_2]\n")

    run_git(manifest_path, "checkout", "-b", "dev")
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "new version - dev")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # set to new manifest branch
    tsrc_cli.run("manifest", "--branch", "dev")

    # change Deep Manifest
    with open(manifest_path / "manifest.yml", "a") as dm_file:
        dm_file.write("  group_3:\n    repos: [repo_1]\n")

    # HERE: DM leftover ('repo_1') will be displayed
    #   only DM repo is displayed that match configured Group ('repo_1')
    #   all FM repos is displayed due to by default config is updated
    #   with it also Groups is updated (unless '--no-update-config')
    #   according to Future Manifest's defined Groups.
    message_recorder.reset()
    tsrc_cli.run("status")

    assert message_recorder.find(
        r"=> Destination \[Deep Manifest description\] \(Future Manifest description\)"
    )
    assert message_recorder.find(
        r"\* manifest            \(        << dev \) \(dirty\) \(expected: master\) ~~ MANIFEST"
    )
    assert message_recorder.find(r"\* repo_4              \(        << master \)")
    assert message_recorder.find(r"\* repo_5              \(        << master \)")
    assert message_recorder.find(r"\* repo_3              \(        << master \)")
    assert message_recorder.find(r"- repo_1   \[ master \] \( master << ::: \)")
    assert message_recorder.find(r"\+ repo_2              \( master == master \)")

    # put changes so it can be seen in apprise block (FM comparsion)
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "extra group_3")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # now with requrested Groups
    message_recorder.reset()
    tsrc_cli.run("status", "--groups", "group_3", "group_4", "group_5")
    assert message_recorder.find(
        r"=> Destination \[Deep Manifest description\] \(Future Manifest description\)"
    )
    assert message_recorder.find(r"\* repo_3              \(        << master \)")
    assert message_recorder.find(r"\* repo_5              \(        << master \)")
    assert message_recorder.find(
        r"\* manifest            \(        << dev \) \(expected: master\) ~~ MANIFEST"
    )
    assert message_recorder.find(r"\* repo_4              \(        << master \)")
    assert message_recorder.find(r"- repo_1   \[ master \] \( master << ::: \)")

    message_recorder.reset()
    tsrc_cli.run("sync")
    assert message_recorder.find(r"=> Updating Workspace Groups configuration")

    # test how does 'config.yml' ends up
    is_ok: int = 0
    with open(Path(".tsrc") / "config.yml", "r") as cfgf:
        this_config_lines = cfgf.read()
        if (
            "group_4" in this_config_lines
            or "group_5" in this_config_lines  # noqa: 503
            or "group_all" in this_config_lines  # noqa: 503
        ):
            raise AssertionError("config contains wrong groups")
        else:
            if "group_3" in this_config_lines:
                is_ok += 1

    if is_ok != 1:
        raise AssertionError("config contains wrong groups")

    # just 1 repo should be synced
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* repo_1 master")
    assert not message_recorder.find(r"\* repo_[2-9]")


def test_sync__group__fm_no_groups(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    when going to sync:
    configured Groups, but not specified
    but Deep Manifest does not have any Groups defined
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

    tsrc_cli.run("dump-manifest", "--raw", ".", "--save-to", "later_manifest.yml")

    """
    ====================================================
    now: let us create Workspace with Repos and Manifest
    """

    git_server.add_repo("repo_3")
    git_server.push_file("repo_3", "repo_3_file.txt")
    git_server.add_repo("repo_4")
    git_server.push_file("repo_4", "repo_4_file.txt")
    git_server.add_repo("repo_5")
    git_server.push_file("repo_5", "repo_5_file.txt")
    manifest_url = git_server.manifest_url

    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    git_server.add_group("group_3", ["manifest", "repo_3"])
    git_server.add_group("group_4", ["manifest", "repo_4"])
    git_server.add_group("group_5", ["manifest", "repo_5"])

    # git_server.manifest.configure_group("group_3", ["manifest", "repo_3"])

    tsrc_cli.run("init", "--branch", "master", manifest_url)
    tsrc_cli.run("sync")
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # move previous repos so we can determine if they ware brought back again
    shutil.move(workspace_path / "repo_1", workspace_path / "__repo_1")

    """
    ==========
    now: introduce previous manifest
    """

    shutil.copyfile("later_manifest.yml", Path("manifest") / "manifest.yml")
    manifest_path = workspace_path / "manifest"

    # write groups to manifest
    # with open(manifest_path / "manifest.yml", "a") as dm_file:
    #     dm_file.write("groups:\n  group_all:\n    repos: [repo_1, repo_2]\n")

    run_git(manifest_path, "checkout", "-b", "dev")
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "new version - dev")
    run_git(manifest_path, "push", "-u", "origin", "dev")

    # set to new manifest branch
    tsrc_cli.run("manifest", "--branch", "dev")

    # status: we did not specify Groups, there are configured Groups
    #   but that does not hold Deep Manifest back
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(
        r"=> Destination \[Deep Manifest description\] \(Future Manifest description\)"
    )
    assert message_recorder.find(r"\* repo_3              \(        << master \)")
    assert message_recorder.find(
        r"\* manifest            \(        << dev \) \(expected: master\) ~~ MANIFEST"
    )
    assert message_recorder.find(r"\* repo_4              \(        << master \)")
    assert message_recorder.find(r"\* repo_5              \(        << master \)")
    assert message_recorder.find(r"- repo_1   \[ master \] \( master << ::: \)")
    assert message_recorder.find(r"\+ repo_2   \[ master \] \( master == master \)")

    tsrc_cli.run("sync")

    # at last verify status
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* repo_1 master")
    assert message_recorder.find(r"\* repo_2 master")
    assert not message_recorder.find(r"\* repo_[3-9]")
