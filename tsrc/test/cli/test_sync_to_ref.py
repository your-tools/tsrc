"""
Sync to Ref

when you provide Ref in Manifest file
(meaning: SHA1 or Tag)
than calling plain `git reset --hard`
can cause unforseen consequences in some cases.

Therefore some preparation need to take place
(see 'sync_repo_to_ref_and_branch' Fn of 'syncer.py' and
'sync_repo_to_sha1_and_branch' respectively)

Here we will test such border cases when without
such preparation taking plase, these test will surelly fail.

    Background:

    New Manifest's branch contains manifest.yml file
    that is using different branch for given repository
    AND ALSO specifying ref (SHA1 or Tag)
    and is on different commit (that can be fast-forward)
    Calling `git reset --hard <sha1>`
    efectively ignore provided branch and set current branch
    to configured ref.

    This is not acceptable as each reference can have more
    branches linked to it. And we may not want current branch
    to be checked out to configured ref.
    Thus keeping the status quo regarding respecting branch on
    which it ends up is a must.

    Here we test such feature that ensure just that.

    If Manifest is configured to use Tag and branch, Tag is
    firstly translated to SHA1 of such commit and than used
    in same way as if there was SHA1 in the first place.
"""

from pathlib import Path
from typing import List

# import pytest
import ruamel.yaml
from cli_ui.tests import MessageRecorder

from tsrc.git import run_git, run_git_captured
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer
from tsrc.workspace_config import WorkspaceConfig


def test_sync_to_ref_case_1(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Scenario:

    * 1st: Create repository
    * 2nd: add Manifest repository
    * 3rd: init workspace on master
    * 4th: play with Workspace Repo
        * checkout branch 'dev'
        * add changes to file
        * add tag
        * push it all to 'origin'
    * 5th: add more branches to same commit
        to be sure it is able to choose the right one
    * 6th: obtain SHA1 of such prepared (remote) branch
    * 7th: return back to 'master'
    * 8th: play with Manifest Repo

            vvvvvvvvvvv
    * 9th: CASE SPECIFIC: update Manifest with SHA1
            ^^^^^^^^^^^

    * 10th: add, commit and push changes
    * 11th: now switch Manifest's branch
    * 12th: sync
    * 13th: check status after sync
        here we can see if it was synced properly
    """

    # 1st: Create repository
    git_server.add_repo("main-proj-backend")
    git_server.push_file("main-proj-backend", "CMakeLists.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: play with Workspace Repo
    #   * checkout branch 'dev'
    #   * add changes to file
    #   * add tag
    #   * push it all to 'origin'
    backend_path: Path = workspace_path / "main-proj-backend"
    run_git(backend_path, "checkout", "-b", "dev")
    with open(backend_path / "CMakeLists.txt", "a") as this_file:
        this_file.write("adding some more data")
    run_git(backend_path, "add", "CMakeLists.txt")
    run_git(backend_path, "commit", "-m", "'extending data'")
    run_git(backend_path, "push", "-u", "origin", "dev")
    run_git(backend_path, "tag", "-a", "v1.0", "-m", "'on new version'")

    # 5th: add more branches to same commit
    #   to be sure it is able to choose the right one
    run_git(backend_path, "checkout", "-b", "another")
    run_git(backend_path, "push", "-u", "origin", "another")
    run_git(backend_path, "checkout", "-b", "not_u")
    run_git(backend_path, "push", "origin", "not_u")
    run_git(backend_path, "push", "--all")

    # 6th: obtain SHA1 of such prepared (remote) branch
    _, ret = run_git_captured(
        backend_path, "ls-remote", "--exit-code", "--head", "origin", "refs/heads/dev"
    )
    backend_sha1 = ret.split()[0]

    # 7th: return back to 'master'
    run_git(backend_path, "checkout", "master")

    # 8th: play with Manifest Repo
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-b", "cmp-1")

    # 9th: CASE SPECIFIC: update Manifest with SHA1
    ad_hoc_update_dm_repo_branch_and_sha1(workspace_path, backend_sha1)

    # 10th: add, commit and push changes
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "'new composition'")
    run_git(manifest_path, "push", "-u", "origin", "cmp-1")

    # 11th: now switch Manifest's branch
    tsrc_cli.run("manifest", "--branch", "cmp-1")

    # 12th: sync
    tsrc_cli.run("sync")

    # 13th: check status after sync
    #   here we can see if it was synced properly
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* main-proj-backend \[ dev   \]  dev on v1.0")
    assert message_recorder.find(r"\* manifest          \[ cmp-1 \]= cmp-1 ~~ MANIFEST")
    assert message_recorder.find(r"=> Destination \[Deep Manifest description\]")


def test_sync_to_ref_case_2(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Scenario:

    * 1st: Create repository
    * 2nd: add Manifest repository
    * 3rd: init workspace on master
    * 4th: play with Workspace Repo
        * checkout branch 'dev'
        * add changes to file
        * add tag
        * push it all to 'origin'
    * 5th: add more branches to same commit
        to be sure it is able to choose the right one
    * 6th: obtain SHA1 of such prepared (remote) branch
    * 7th: return back to 'master'
    * 8th: play with Manifest Repo

            vvvvvvvvvvv
    * 9th: CASE SPECIFIC: deliberately delete local 'dev' branch
        so we will force the checkout of 'dev' branch
        and update manifest with SHA1
            ^^^^^^^^^^^

    * 10th: add, commit and push changes
    * 11th: now switch Manifest's branch
    * 12th: sync
    * 13th: check status after sync
        here we can see if it was synced properly
    """

    # 1st: Create repository
    git_server.add_repo("main-proj-backend")
    git_server.push_file("main-proj-backend", "CMakeLists.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: play with Workspace Repo
    #   * checkout branch 'dev'
    #   * add changes to file
    #   * add tag
    #   * push it all to 'origin'
    backend_path: Path = workspace_path / "main-proj-backend"
    run_git(backend_path, "checkout", "-b", "dev")
    with open(backend_path / "CMakeLists.txt", "a") as this_file:
        this_file.write("adding some more data")
    run_git(backend_path, "add", "CMakeLists.txt")
    run_git(backend_path, "commit", "-m", "'extending data'")
    run_git(backend_path, "push", "-u", "origin", "dev")
    run_git(backend_path, "tag", "-a", "v1.0", "-m", "'on new version'")

    # 5th: add more branches to same commit
    #   to be sure it is able to choose the right one
    run_git(backend_path, "checkout", "-b", "another")
    run_git(backend_path, "push", "-u", "origin", "another")
    run_git(backend_path, "checkout", "-b", "not_u")
    run_git(backend_path, "push", "origin", "not_u")
    run_git(backend_path, "push", "--all")

    # 6th: obtain SHA1 of such prepared (remote) branch
    _, ret = run_git_captured(
        backend_path, "ls-remote", "--exit-code", "--head", "origin", "refs/heads/dev"
    )
    backend_sha1 = ret.split()[0]

    # 7th: return back to 'master'
    run_git(backend_path, "checkout", "master")

    # 8th: play with Manifest Repo
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-b", "cmp-1")

    # 9th: CASE SPECIFIC: deliberately delete local 'dev' branch
    #   so we will force the checkout of 'dev' branch
    run_git(backend_path, "branch", "-D", "dev")
    #   and update manifest with SHA1
    ad_hoc_update_dm_repo_branch_and_sha1(workspace_path, backend_sha1)

    # 10th: add, commit and push changes
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "'new composition'")
    run_git(manifest_path, "push", "-u", "origin", "cmp-1")

    # 11th: now switch Manifest's branch
    tsrc_cli.run("manifest", "--branch", "cmp-1")

    # 12th: sync
    tsrc_cli.run("sync")

    # 13th: check status after sync
    #   here we can see if it was synced properly
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* main-proj-backend \[ dev   \]  dev on v1.0")
    assert message_recorder.find(r"\* manifest          \[ cmp-1 \]= cmp-1 ~~ MANIFEST")
    assert message_recorder.find(r"=> Destination \[Deep Manifest description\]")


def test_sync_bug_unique_case_3(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Scenario:

    * 1st: Create repository
    * 2nd: add Manifest repository
    * 3rd: init workspace on master
    * 4th: play with Workspace Repo
        * checkout branch 'dev'
        * add changes to file
        * add tag
        * push it all to 'origin'
    * 5th: add more branches to same commit
        to be sure it is able to choose the right one

            vv
    * 6th: SKIP: obtain SHA1 of such prepared (remote) branch
            ^^

    * 7th: return back to 'master'
    * 8th: play with Manifest Repo

            vvvvvvvvvvv                        vvv
    * 9th: CASE SPECIFIC: update Manifest with Tag
            ^^^^^^^^^^^                        ^^^

    * 10th: add, commit and push changes
    * 11th: now switch Manifest's branch
    * 12th: sync
    * 13th: check status after sync
        here we can see if it was synced properly
    """

    # 1st: Create repository
    git_server.add_repo("main-proj-backend")
    git_server.push_file("main-proj-backend", "CMakeLists.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: play with Workspace Repo
    #   * checkout branch 'dev'
    #   * add changes to file
    #   * add tag
    #   * push it all to 'origin'
    backend_path: Path = workspace_path / "main-proj-backend"
    run_git(backend_path, "checkout", "-b", "dev")
    with open(backend_path / "CMakeLists.txt", "a") as this_file:
        this_file.write("adding some more data")
    run_git(backend_path, "add", "CMakeLists.txt")
    run_git(backend_path, "commit", "-m", "'extending data'")
    run_git(backend_path, "push", "-u", "origin", "dev")
    run_git(backend_path, "tag", "-a", "v1.0", "-m", "'on new version'")

    # 5th: add more branches to same commit
    #   to be sure it is able to choose the right one
    run_git(backend_path, "checkout", "-b", "another")
    run_git(backend_path, "push", "-u", "origin", "another")
    run_git(backend_path, "checkout", "-b", "not_u")
    run_git(backend_path, "push", "origin", "not_u")
    run_git(backend_path, "push", "--all")

    # ### CASE SPECIFIC ###
    # 6th: SKIP: obtain SHA1 of such prepared (remote) branch
    pass

    # 7th: return back to 'master'
    run_git(backend_path, "checkout", "master")

    # 8th: play with Manifest Repo
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-b", "cmp-1")

    # 9th: CASE SPECIFIC: update Manifest with Tag
    ad_hoc_update_dm_repo_branch_and_tag(workspace_path, "v1.0")

    # 10th: add, commit and push changes
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "'new composition'")
    run_git(manifest_path, "push", "-u", "origin", "cmp-1")

    # 11th: now switch Manifest's branch
    tsrc_cli.run("manifest", "--branch", "cmp-1")

    # 12th: sync
    tsrc_cli.run("sync")

    # 13th: check status after sync
    #   here we can see if it was synced properly
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* main-proj-backend \[ dev on v1.0 \]  dev on v1.0")
    assert message_recorder.find(
        r"\* manifest          \[ cmp-1       \]= cmp-1 ~~ MANIFEST"
    )
    assert message_recorder.find(r"=> Destination \[Deep Manifest description\]")


def ad_hoc_update_dm_repo_branch_and_sha1(
    workspace_path: Path,
    devs_sha1: str,
) -> None:
    """change Repo's branch and SHA1"""
    manifest_path = workspace_path / "manifest" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())

    for _, value in parsed.items():
        if isinstance(value, List):
            for x in value:
                if isinstance(x, ruamel.yaml.comments.CommentedMap):
                    if "dest" in x:
                        if x["dest"] == "main-proj-backend":
                            x["branch"] = "dev"
                            x["sha1"] = devs_sha1
                        if x["dest"] == "manifest":
                            x["branch"] = "cmp-1"
    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)


def ad_hoc_update_dm_repo_branch_and_tag(
    workspace_path: Path,
    this_tag: str,
) -> None:
    """change Repo's branch and Tag"""
    manifest_path = workspace_path / "manifest" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())

    for _, value in parsed.items():
        if isinstance(value, List):
            for x in value:
                if isinstance(x, ruamel.yaml.comments.CommentedMap):
                    if "dest" in x:
                        if x["dest"] == "main-proj-backend":
                            x["branch"] = "dev"
                            x["tag"] = this_tag
                        if x["dest"] == "manifest":
                            x["branch"] = "cmp-1"
    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)
