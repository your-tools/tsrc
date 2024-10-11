from pathlib import Path
from shutil import copyfile

# import pytest
from cli_ui.tests import MessageRecorder

from tsrc.git import run_git
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer
from tsrc.test.helpers.manifest_file import (
    ad_hoc_deep_manifest_manifest_branch,
    ad_hoc_deep_manifest_manifest_url,
)
from tsrc.workspace_config import WorkspaceConfig


def test_manifest__no_dm(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Make sure that when we disable Deep Manifest (--no-dm)
    the Local Manifest Repo will still be displayed.
    This occurs on 'manifest' command only

    Scenario:

    * 1st: Create repositories and Manifest repository as well
    * 2nd: init Workspace on master
    * 3rd: check Local Manifest Repo, without Deep Manifest
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

    # 3rd: check Local Manifest Repo, without Deep Manifest
    message_recorder.reset()
    tsrc_cli.run("manifest", "--no-dm")
    assert message_recorder.find(
        r"\* manifest master ~~ MANIFEST"
    ), "ignoring Deep Manifest blocking displaying Local Manifest Repo"


def test_plain_manifest_on_change(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """Scenario:
    * 1st: Create repository
    * 2nd: init Workspace
    * 3rd: check for Manifest branch configured for Workspace
    * 4th: change branch using 'manifest --branch <new_branch>' command
    * 5th: check again if Manifest branch has changed and if output is reflecting it
    * 6th: also check output of plain 'manifest' command
        as it should also reflect such branch change
    """
    # 1st: Create repository
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    manifest_url = git_server.manifest_url
    git_server.manifest.change_branch("devel")

    # 2nd: init Workspace
    tsrc_cli.run("init", "--branch", "devel", manifest_url)

    # 3rd: check for Manifest branch configured for Workspace
    workspace_config = WorkspaceConfig.from_file(
        workspace_path / ".tsrc" / "config.yml"
    )

    assert git_server.manifest.branch == "devel"

    # 4th: change branch using 'manifest --branch <new_branch>' command
    message_recorder.reset()
    tsrc_cli.run("manifest", "--branch", "master")

    # 5th: check again if Manifest branch has changed and if output is reflecting it
    workspace_config = WorkspaceConfig.from_file(
        workspace_path / ".tsrc" / "config.yml"
    )
    assert workspace_config.manifest_branch == "master"
    assert workspace_config.manifest_branch_0 == "devel"
    assert message_recorder.find(
        r"=> Accepting Manifest\'s branch change from: devel ~~> master"
    ), "manifest command has to report change when different branch is provided"

    # 6th: also check output of plain 'manifest' command if also reflecting change
    message_recorder.reset()
    tsrc_cli.run("manifest")
    assert message_recorder.find(
        r":: Manifest\'s branch will change from: devel ~~> master"
    ), "manifest command has to report change when there is one"


def test_deep_manifest_on_change_after_sync(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """Scenario:
    * 1st: Create repository
    * 2nd: add (own) Manifest repository to itself
    * 3rd: init Workspace
    * 4th: change manifest repository branch
    * 5th: fix 'missing upstream'
    * 6th: chage manifest branch using 'manifest' command
    * 7th: read 'manifest.yml', write there that 'manifest' will be using 'devel' branch
    * 8th: commit and push changes, so Manifest repository will not be dirty
    * 9th: check final output of 'manifest' command
    * 10th: verify the theory about what will happen after 'sync'
    """
    # 1st: Create repository
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeList.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add (own) Manifest repository to itself
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init Workspace
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")
    assert git_server.manifest.branch == "master"
    tsrc_cli.run("sync")

    # 4th: change manifest repository branch
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-B", "devel")

    # 5th: fix 'missing upstream'
    message_recorder.reset()
    run_git(manifest_path, "push", "-u", "origin", "devel")

    # 6th: chage manifest branch using 'manifest' command
    tsrc_cli.run("manifest", "--branch", "devel")

    # 7th: read 'manifest.yml', write there that 'manifest' will be using 'devel' branch
    ad_hoc_deep_manifest_manifest_branch(workspace_path, "devel")

    # 8th: commit and push changes, so Manifest repository will not be dirty
    run_git(
        manifest_path,
        "commit",
        "-a",
        "-m",
        "updating manifest repository to branch: devel",
    )
    run_git(manifest_path, "push")

    # 9th: check final output of 'manifest' command
    message_recorder.reset()
    tsrc_cli.run("manifest")
    assert message_recorder.find(
        r"\* manifest \[ devel \]= \( devel == devel \) \(expected: master\) ~~ MANIFEST"
    )
    assert message_recorder.find(r"=> Before possible GIT statuses, Workspace reports:")
    assert message_recorder.find(
        r"=> Destination \[Deep Manifest description\] \(Future Manifest description\)"
    )

    # 10th: verify the theory about what will happen after 'sync'
    tsrc_cli.run("sync")
    message_recorder.reset()
    tsrc_cli.run("manifest")
    assert message_recorder.find(r"\* manifest \[ devel \]= devel ~~ MANIFEST")
    assert message_recorder.find(r"=> Destination \[Deep Manifest description\]")
    assert not message_recorder.find(
        r"=> Destination \[Deep Manifest description\] \(Future Manifest description\)"
    ), "there should not bee any Future Manifest description"


def test_deep_manifest_with_different_remote_url_for_its_manifest_repo(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """Scenario:
    * 1st: create repo, create (own) manifest repo and init workspace
    * 2nd: add another "m2" repo
    * 3rd: copy 'manifest.yml' from manfiest repo to "m2"
    * 4th: change file 'manifest.yml' in manifest repo to use different url
        for 'manifest' record
    * 5th: check if 'manifest' report dirty manifest repository
    * 6th: fix dirty: git add, commit, push
    * 7th: let us see now if 'manifest' command report this state correctly
    """
    # 1st: create repo, create (own) manifest repo and init workspace
    git_server.add_repo("dummy_repo")
    git_server.push_file("dummy_repo", "CMakeList.txt")
    git_server.add_manifest_repo("manifest")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)

    # 2nd: add another "m2" repo
    manifest_path = workspace_path / "manifest"
    m2_url = git_server.add_repo("m2")
    tsrc_cli.run("sync")
    tsrc_cli.run("manifest")

    # 3rd: copy 'manifest.yml' to new "m2" directory
    m2_path = workspace_path / "m2"
    copyfile(manifest_path / "manifest.yml", m2_path / "manifest.yml")

    # 4th: change file 'manifest.yml' in manifest repo to use different url
    #    for 'manifest' record
    ad_hoc_deep_manifest_manifest_url(workspace_path, m2_url)

    # 5th: check if 'manifest' report dirty manifest repository
    message_recorder.reset()
    tsrc_cli.run("manifest")
    assert message_recorder.find(r"\* manifest master \(dirty\) ~~ MANIFEST")

    # 6th: fix dirty: git add, commit, push
    run_git(manifest_path, "add", "manifest.yml")
    run_git(
        manifest_path, "commit", "-m", "manifest.yml: changing url for manifest repo"
    )
    run_git(manifest_path, "push", "origin", "master")

    # 7th: let us see now if 'manifest' command report this state correctly
    message_recorder.reset()
    tsrc_cli.run("manifest")
    assert message_recorder.find(
        # TODO: enable this check once status footer will be implemented
        # "=> Deep manifest is using different remote URL for its manifest"
        r"\* manifest master ~~ MANIFEST"
    )
    assert message_recorder.find(r"=> Before possible GIT statuses, Workspace reports:")
    assert message_recorder.find(r"=> Destination")
    # what we should not find
    assert not message_recorder.find(r"=> Destination \[Deep Manifest description\]")
    assert not message_recorder.find(r"=> Destination \(Future Manifest description\)")

    # assert message_recorder.find(":: Deep Manifest's manifest repo URL:")


def test_manifest_changing_upstream_remote(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """Reason:
    We are testing if 'tsrc manifest' can detect that
    configured remote of Deep Manifest
    has change regardles of how data looks like.

    This is not usual case what can happen to Manifest repository,
    or any repository for that matter, however we have to be sure
    that we have what is configured and thus expected.

    Without this we cannot guarantee what will happen after 'sync'

    Scenario:
    * 1st: create dummy_repo, manifest (own) repo and init Workspace
    * 2nd: create yet another repo "m2" in workspace
    * 3rd: copy 'manifest.yml' to new "m2" directory
    * 4th: add, commit and push it to remote
    * 5th: now let us set different (git) remote to "manifest" repository
    * 6th: now the remotes should not be the same
    """

    # 1st: create dummy_repo, manifest (own) repo and init Workspace
    git_server.add_repo("dummy_repo")
    git_server.push_file("dummy_repo", "CMakeList.txt")
    git_server.add_manifest_repo("manifest")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)

    # 2nd: create yet another repo "m2" in workspace
    manifest_path = workspace_path / "manifest"
    m2_url = git_server.add_repo("m2")
    tsrc_cli.run("sync")
    tsrc_cli.run("manifest")

    # 3rd: copy 'manifest.yml' to new "m2" directory
    m2_path = workspace_path / "m2"
    copyfile(manifest_path / "manifest.yml", m2_path / "manifest.yml")

    # 4th: add, commit and push it to remote
    run_git(m2_path, "add", "manifest.yml")
    run_git(m2_path, "commit", "-m", "puting manifest.yml file up there")
    run_git(m2_path, "push", "origin", "master")

    # 5th: now let us set different (git) remote to "manifest" repository
    """make a note here: we have added the remote of'm2'
    repository which contains exactly the same manifest
    as original 'manifest' repository has. So all data
    is exactly the same as before, only thing that has
    changed is (git) remote"""
    run_git(manifest_path, "remote", "add", "r2", m2_url)
    run_git(manifest_path, "branch", "--unset-upstream")
    run_git(manifest_path, "branch", "--track", "r2/master")
    run_git(manifest_path, "branch", "--set-upstream-to=r2/master")

    # 6th: now the remotes should not be the same
    message_recorder.reset()
    tsrc_cli.run("manifest")
    # TODO: enable this check once status footer will be implemented
    # assert message_recorder.find("=> Remote branch does not have same HEAD")
    assert message_recorder.find(r"\* manifest \[ master \]= master ~~ MANIFEST")
    assert message_recorder.find(r"=> Before possible GIT statuses, Workspace reports:")
    assert message_recorder.find(r"=> Destination \[Deep Manifest description\]")
    # what we should not find
    assert not message_recorder.find(r"=> Destination \(Future Manifest description\)")
    assert not message_recorder.find(
        r"=> Destination \[Deep Manifest description\] \(Future Manifest description\)"
    )


def test_manifest_cmd_branch(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Scenario:
    * 1st: Create repository
    * 2nd: init Workspace
    * 3rd: check manifest branch
    * 4th: change manifest branch
    * 5th: check after change
    * 6th: change manifest branch back (to see if message report is corret)
    * 7th: check after change
    * 8th: change to wrong branch (non-existant)
    * 9th: change to already present branch (should not change)
    """

    # 1st: Create repository
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    manifest_url = git_server.manifest_url
    git_server.manifest.change_branch("devel")

    # 2nd: init Workspace
    tsrc_cli.run("init", "--branch", "devel", manifest_url)

    # 3rd: check manifest branch
    message_recorder.reset()
    tsrc_cli.run("manifest")
    assert message_recorder.find(r":: Manifest's branch: devel")

    # 4th: change manifest branch
    message_recorder.reset()
    tsrc_cli.run("manifest", "--branch", "master")
    assert message_recorder.find(
        r"=> Accepting Manifest's branch change from: devel ~~> master"
    )

    # 5th: check after change
    message_recorder.reset()
    tsrc_cli.run("manifest")
    assert message_recorder.find(
        r":: Manifest's branch will change from: devel ~~> master"
    )

    # 6th: change manifest branch back (to see if message report is corret)
    message_recorder.reset()
    tsrc_cli.run("manifest", "--branch", "devel")
    assert message_recorder.find(
        r"=> Reverting previous update, Manifest's branch will stays on: devel"
    )

    # 7th: check after change
    message_recorder.reset()
    tsrc_cli.run("manifest")
    assert message_recorder.find(r":: Manifest's branch: devel")

    # 8th: change to wrong branch (non-existant)
    message_recorder.reset()
    tsrc_cli.run("manifest", "--branch", "xxx")
    assert message_recorder.find(
        r"=> Such Manifest's branch: xxx was not found on remote, ignoring"
    ), "manifest branch change must be resistant against non-existant branch"
    assert message_recorder.find(
        r":: Manifest's branch: devel"
    ), "report that wrong value does not impact current state"

    # 9th: change to already present branch (should not change)
    message_recorder.reset()
    tsrc_cli.run("manifest", "--branch", "devel")
    assert message_recorder.find(
        r"=> No change to Manifest's branch, it will still stays on: devel"
    )
