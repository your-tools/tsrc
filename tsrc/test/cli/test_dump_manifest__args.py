import os
from pathlib import Path

# import pytest
from cli_ui.tests import MessageRecorder

from tsrc.git import run_git
from tsrc.manifest import load_manifest
from tsrc.test.cli.test_dump_manifest import ad_hoc_delete_remote_from_manifest
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer
from tsrc.workspace_config import WorkspaceConfig

"""
Contains:

* test_wrong_args__raw_update__missing_workspace
* test_raw_dump_update__with_workspace__do_update__ok
* test_raw_dump_update__with_workspace__do_update__fail
* test_raw_dump_update__with_workspace__do_update__force
* test_raw_dump_update_with_multi_remotes__use_workspace__dirty__fail
* test_wrong_args__save_to_overwrite
* test_wrong_args__update_on_file
* test_wrong_args__update_and_update_on
* test_wrong_args__save_to_path
* test_wrong_args__update_on
* test_wrong_args__update
* test_wrong_args__save_to_update_on
"""


def test_raw_dump_update__with_workspace__do_update__ok(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Combination of RAW dump and Workspace Deep Manifest upate

    Option A: resonable and correct way

    Scenario:

    * 1st: Create repositories
    * 2nd: add Manifest repository
    * 3nd: init workspace on master
    * 4th: create sub-dircetory for RAW dump (will be used later)
    * 5th: introduce 'repo 3' ignoring Workpsace
    * 6th: option A: RAW dump starting from '.' dir (reasonable)
    """
    # 1st: Create repositories
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "CMakeLists.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3nd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: create sub-dircetory for RAW dump (will be used later)
    sub1_path = "level 2"
    os.makedirs(sub1_path)

    # 5th: introduce 'repo 3' ignoring Workpsace
    os.chdir(sub1_path)
    sub1_1_path = Path("repo 3")
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)
    full1_path: Path = Path(os.path.join(workspace_path, sub1_path, sub1_1_path))
    run_git(full1_path, "init")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full1_path, "add", "in_repo.txt")
    run_git(full1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")

    # 6th: option A: RAW dump starting from '.' dir (reasonable)
    os.chdir(workspace_path)
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--raw", ".", "--update", "--preview")

    # 'repo 3' should be included in output
    assert message_recorder.find(r"dest: manifest")
    assert message_recorder.find(
        r"level 2.*repo 3"
    ), "Update on Deep Manifest was NOT successful"


def test_raw_dump_update__with_workspace__do_update__fail(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Combination of RAW dump and Workspace Deep Manifest upate

    Option B: not reasonable way, should FAIL

    Scenario:

    * 1st: Create repositories
    * 2nd: add Manifest repository
    * 3nd: init workspace on master
    * 4th: create sub-dircetory for RAW dump (will be used later)
    * 5th: introduce 'repo 3' ignoring Workpsace
    * 6th: option B: RAW dump starting from 'level 2' dir (NOT reasonable)
    """
    # 1st: Create repositories
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "CMakeLists.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3nd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: create sub-dircetory for RAW dump (will be used later)
    sub1_path = "level 2"
    os.makedirs(sub1_path)

    # 5th: introduce 'repo 3' ignoring Workpsace
    os.chdir(sub1_path)
    sub1_1_path = Path("repo 3")
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)
    full1_path: Path = Path(os.path.join(workspace_path, sub1_path, sub1_1_path))
    run_git(full1_path, "init")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full1_path, "add", "in_repo.txt")
    run_git(full1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")

    # 6th: option B: RAW dump starting from 'level 2' dir (NOT reasonable)
    os.chdir(workspace_path)
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--raw", "level 2", "--update")

    assert message_recorder.find(
        r"Error: Please consider again what you are trying to do."
    )


def test_raw_dump_update__with_workspace__do_update__force(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Combination of RAW dump and Workspace Deep Manifest upate

    Option C: using force (testing by load_manifest())

    Scenario:

    * 1st: Create repositories
    * 2nd: add Manifest repository
    * 3nd: init workspace on master
    * 4th: create sub-dircetory for RAW dump (will be used later)
    * 5th: introduce 'repo 3' ignoring Workpsace
    * 6th: option C: RAW dump starting from 'level 2' dir with '--force'
    """

    # 1st: Create repositories
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    repo2_url = git_server.add_repo("repo2")
    git_server.push_file("repo2", "CMakeLists.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3nd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: create sub-dircetory for RAW dump (will be used later)
    sub1_path = "level 2"
    os.makedirs(sub1_path)

    # 5th: introduce 'repo 3' ignoring Workpsace
    os.chdir(sub1_path)
    sub1_1_path = Path("repo 3")
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)
    full1_path: Path = Path(os.path.join(workspace_path, sub1_path, sub1_1_path))
    run_git(full1_path, "init")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full1_path, "add", "in_repo.txt")
    run_git(full1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    run_git(full1_path, "remote", "add", "origin", repo2_url)

    # 6th: option C: RAW dump starting from 'level 2' dir with '--force'
    os.chdir(workspace_path)
    message_recorder.reset()
    tsrc_cli.run(
        "dump-manifest",
        "--raw",
        "level 2",
        "--update",
        "--force",
    )

    # 7th: check Manifest by load_manifest
    is_fail: bool = False
    is_ok: bool = False
    w_m_path = workspace_path / "manifest" / "manifest.yml"
    m = load_manifest(w_m_path)
    for repo in m.get_repos():
        if repo.dest == "repo 3":
            is_ok = True
        # if repo.dest == "repo1" or repo.dest == "repo2" or repo.dest == "manifest":
        if repo.dest in ["repo1", "repo2", "manifest"]:
            is_fail = True
    if is_fail is True or is_ok is False:
        raise Exception("Found wrong repos in Manifest")


def test_raw_dump_update__repo_dirty__still_updates(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    when Deep Manifest is dirty, however
    Manifest file 'manifest.yml' is clean,
    allow update

    Scenario:
    * 1st: Create repositories (1x multiple remotes)
    * 2nd: add Manifest repository
    * 3rd: init workspace on master
    * 4th: DM: add file, so the repository will look dirty
    * 5th: OK: as 'manifest.yml' is not dirty, allow update
    """
    # 1st: Create repositories (1x multiple remotes)
    #   'repo1-mr' will have multiple remotes
    repo1_url = git_server.add_repo("repo1-mr")
    git_server.push_file("repo1-mr", "CMakeLists.txt")
    git_server.manifest.set_repo_remotes(
        "repo1-mr", [("origin", repo1_url), ("upstream", "git@upstream.com")]
    )
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "test.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: DM: add file, so the repository will look dirty
    Path(workspace_path / "manifest" / "dirty.test").touch()
    run_git(workspace_path / "manifest", "add", "dirty.test")

    # 5th: OK: as 'manifest.yml' is not dirty, allow update
    #   even though repository in fact IS dirty
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--raw", ".", "--update")

    assert message_recorder.find(
        r"=> UPDATING Deep Manifest on '.*manifest.*manifest\.yml'"
    )
    assert message_recorder.find(r":: Dump complete")


def test_raw_dump_update_with_multi_remotes__use_workspace__dirty__fail(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    test if updating Deep Manifest is blocked
    when its Repo is dirty

    this is done by early data check (before obtaining YAML data)

    Scenario:
    * 1st: Create repositories (1x multiple remotes)
    * 2nd: add Manifest repository
    * 3rd: init workspace on master
    * 4th: remove "origin" remote from 'manifest/manifest.yml"
    * 5th: FAIL: does not allow update on dirty Deep Manifest
    * 6th: no fail when using '--preview'
    """
    # 1st: Create repositories (1x multiple remotes)
    #   'repo1-mr' will have multiple remotes
    repo1_url = git_server.add_repo("repo1-mr")
    git_server.push_file("repo1-mr", "CMakeLists.txt")
    git_server.manifest.set_repo_remotes(
        "repo1-mr", [("origin", repo1_url), ("upstream", "git@upstream.com")]
    )
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "test.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: remove "origin" remote from 'manifest/manifest.yml"
    manifest_path = workspace_path / "manifest" / "manifest.yml"
    ad_hoc_delete_remote_from_manifest(manifest_path)

    # 5th: FAIL: does not allow update on dirty Deep Manifest
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--raw", ".", "--update")
    assert message_recorder.find(
        r"Error: not updating Deep Manifest as it is dirty, use '--force' to overide"
    )

    # 6th: no fail when using '--preview'
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--raw", ".", "--update", "--preview")
    assert message_recorder.find(r"dest: repo1-mr")
    assert message_recorder.find(r"dest: repo2")
    assert message_recorder.find(r"dest: manifest")


def test_wrong_args__save_to_overwrite(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Test if we get stopped when
    '--save-to <file>' already exists
    AND:
    A) without '--force' => throws Error
    B) with '--force' => should overwrite
    C) wit '--preview' ==> should display

    Scenario

    * 1st: Create repositories, but not Manifest
    * 2nd: init workspace on master
    * 3rd: A) '--save-to': file exists
    * 3rd: B) same, but now with '--force'
    * 3rd: C) same, but now with '--preview'
    """
    # 1st: Create repositories, but not Manifest
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "test-manifest.yml")
    manifest_url = git_server.manifest_url

    # 2nd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 3rd: A) '--save-to': file exists
    message_recorder.reset()
    test_path_1: str = os.path.join("repo2", "test-manifest.yml")
    tsrc_cli.run("dump-manifest", "--save-to", test_path_1)
    assert message_recorder.find(
        r"Error: 'SAVE_TO' file exist, use '--force' to overwrite existing file"
    )

    # 3rd: B) same, but now with '--force'
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--save-to", test_path_1, "--force")
    assert message_recorder.find(r"=> OVERWRITING file '.*repo2.*test-manifest\.yml'")
    assert message_recorder.find(r":: Dump complete")

    # 3rd: C) same, but now with '--preview'
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--save-to", test_path_1, "--preview")
    assert message_recorder.find(r"dest: repo1")
    assert message_recorder.find(r"dest: repo2")


def test_wrong_args__update_on__non_existent_file(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Test if we get stopped when
    '--update-on <file>' when file does not exists
    """

    # 1st: Create repositories, but not Manifest
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "CMakeLists.txt")
    manifest_url = git_server.manifest_url

    # 2nd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 3rd: 'dump-manifest --update-on <file>' should fail
    #   if <file> does not exist
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--update-on", "test-manifest.yml")
    assert message_recorder.find(r"Error: 'UPDATE_AT' file does not exists")


def test_wrong_args__update_and_update_on(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Test if we get stopped when
    '--update' and '--update-on <file>' is provided
    """
    # 1st: Create repositories, but not Manifest
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "CMakeLists.txt")
    manifest_url = git_server.manifest_url

    # 2nd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 3rd: 'dump-manifest --update --update-on <file>' should fail
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--update", "--update-on", "test-manifest.yml")
    assert message_recorder.find(
        r"Error: Use only one out of '--update' or '--update-on' at a time"
    )


def test_wrong_args__save_to_path(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Test if when Workspace does not have Manifest repo,
    the proper Error is reported

    Scenario:
    * 1st: Create repositories, but not Manifest
    * 2nd: init workspace on master
    * 3rd: 'dump-manifest --save-to' should fail
            as provided Path is not existing
    """

    # 1st: Create repositories, but not Manifest
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "CMakeLists.txt")
    manifest_url = git_server.manifest_url

    # 2nd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 3rd: 'dump-manifest --save-to' should fail
    message_recorder.reset()
    test_path_1: str = os.path.join("repo3", "manifest.yml")
    tsrc_cli.run("dump-manifest", "--save-to", test_path_1)
    assert message_recorder.find(
        r"Error: 'SAVE_TO' directory structure must exists, however 'repo3' does not"
    )


def test_wrong_args__update_on(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Test if when Workspace does not have Manifest repo,
    the proper Error is reported

    Scenario:
    * 1st: Create repositories, but not Manifest
    * 2nd: init workspace on master
    * 3rd: 'dump-manifest --update-on' should fail
            as there is no valid Manifest file there
    """

    # 1st: Create repositories, but not Manifest
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "CMakeLists.txt")
    manifest_url = git_server.manifest_url

    # 2nd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 3rd: 'dump-manifest --update-on' should fail
    message_recorder.reset()
    test_path_1: str = os.path.join("repo2", "CMakeLists.txt")
    tsrc_cli.run("dump-manifest", "--update-on", test_path_1)
    assert message_recorder.find(r"Error: Not able to load YAML data")


def test_wrong_args__raw_update__missing_workspace(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    test if when on RAW dump, '--update' must found Workspace
    (it should also be able to find DM, but that is tested elsewhere)

    Scenario:

    * 1st: create 'repo 1', GIT init, add, commit
    * 2nd: create 'repo 2', GIT init, add, commit
    * 3rd: RAW dump with updating DM, should fail
    """

    # 1st: create 'repo 1', GIT init, add, commit
    os.chdir(workspace_path)
    sub1_1_path = Path("repo 1")
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)
    full1_path: Path = Path(os.path.join(workspace_path, workspace_path, sub1_1_path))
    run_git(full1_path, "init")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full1_path, "add", "in_repo.txt")
    run_git(full1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")

    # 2nd: create 'repo 2', GIT init, add, commit
    os.chdir(workspace_path)
    os.chdir(workspace_path)
    sub1_2_path = Path("repo 2")
    os.mkdir(sub1_2_path)
    os.chdir(sub1_2_path)
    full2_path: Path = Path(os.path.join(workspace_path, workspace_path, sub1_2_path))
    run_git(full2_path, "init")
    sub1_2_1_file = Path("in_repo.txt")
    sub1_2_1_file.touch()
    run_git(full2_path, "add", "in_repo.txt")
    run_git(full2_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")

    # 3rd: RAW dump with updating DM, should fail
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--raw", ".", "--update")
    assert message_recorder.find(r"Error: Could not find current workspace")


def test_wrong_args__update__no_dm(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Test if when Workspace does not have Manifest repo,
    the proper Error is reported

    Scenario:
    * 1st: Create repositories, but not Manifest
    * 2nd: init workspace on master
    * 3rd: 'dump-manifest --update' should fail
            as Manifest repository is not in the Workspace
    """

    # 1st: Create repositories, but not Manifest
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "CMakeLists.txt")
    manifest_url = git_server.manifest_url

    # 2nd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 3rd: 'dump-manifest --update' should fail
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--update")
    assert message_recorder.find(
        r"Error: Cannot obtain Deep Manifest from Workspace to update"
    )


def test_wrong_args__save_to_update_on(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    we should know, that Updating has higher importance,
    therefore when '--save-to' and '--update-on' is used
    at the same time, Warning should be shown about
    'SAVE_TO' to be ignored

    Scenario:
    # 1st: Create repositories
    # 2nd: add Manifest repository
    # 3nd: init workspace on master
    # 4th: change branch of Manifest's Repo
    # 5th: dump-manifest with '--save-to' and '--update-on'
    """

    # 1st: Create repositories
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "CMakeLists.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3nd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: change branch of Manifest's Repo
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-b", "dev")

    # 5th: dump-manifest with '--save-to' and '--update-on'
    #   should put a Warning about '--save-to' be ignored
    #   as updating has higher importance
    message_recorder.reset()
    test_path_1: str = os.path.join("repo2", "manifest.yml")
    test_path_2: str = os.path.join("manifest", "manifest.yml")
    tsrc_cli.run(
        "dump-manifest",
        "--save-to",
        test_path_1,
        "--update-on",
        test_path_2,
    )
    assert message_recorder.find(
        r"Warning: 'SAVE_TO' path will be ignored when using '--update-on'"
    )
