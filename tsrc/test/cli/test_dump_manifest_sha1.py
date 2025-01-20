"""
test SHA1 related manifest dump
like: '--sha1-on'
"""

import re
from pathlib import Path

# import pytest
from cli_ui.tests import MessageRecorder

from tsrc.git import run_git, run_git_captured
from tsrc.manifest import load_manifest_safe_mode
from tsrc.manifest_common_data import ManifestsTypeOfData
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer
from tsrc.workspace_config import WorkspaceConfig


# flake8: noqa: C901
def test_dump_when_repo_behind__sha1_on(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    test dump-manifest: (only) create dump when Repo is ahead/behind
    also test '--sha1-off' to disable SHA1 information in the same case

    Scenario:

    # 1st: create repositories representing project
    # 2nd: add there a Manifest Repo
    # 3rd: init Workspace
    # 4th: introduce some changes, make some Repos behind remote
    # 5th: consider reaching some consistant state, thus
    # 6th: create Manifest with SHA1 marks while skipping Manifest Repo
    # 7th: let us update Manifest, but only with its branch (no SHA1)
    # 8th: commit and push such Manifest to remote
    # 9th: adding repos, making them ahead/behind
    ___ here is where the real tests begins ___
    # 10th A: in 3 Repos the SHA1 has to be present
    # 10th B: same but now turn off sha1
    # 11th A: same as 10th, but for RAW dump
    # 11th B: same but now turn off sha1
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

    # 4th: introduce some changes, make some Repos behind remote
    #   simulating development process
    fp = Path(workspace_path / "frontend-proj")
    Path(fp / "latest-changes.txt").touch()
    run_git(fp, "add", "latest-changes.txt")
    run_git(fp, "commit", "-m", "adding latest changes")
    run_git(fp, "push", "origin", "master")

    bp = Path(workspace_path / "backend-proj")
    Path(bp / "latest-changes.txt").touch()
    run_git(bp, "add", "latest-changes.txt")
    run_git(bp, "commit", "-m", "adding latest changes")
    run_git(bp, "push", "origin", "master")

    el = Path(workspace_path / "extra-lib")
    Path(el / "latest-changes.txt").touch()
    run_git(el, "add", "latest-changes.txt")
    run_git(el, "commit", "-m", "adding latest changes")
    run_git(el, "push", "origin", "master")

    # 5th: consider reaching some consistant state, thus
    #   start to create new assembly chain
    #   by checking out new branch on Manifest
    mp = Path(workspace_path / "manifest")
    run_git(mp, "checkout", "-b", "ac_1.0")

    # 6th: create Manifest with SHA1 marks while skipping Manifest Repo
    tsrc_cli.run("dump-manifest", "--sha1-on", "--update", "--skip-manifest-repo")

    # 7th: let us update Manifest, but only with its branch (no SHA1)
    tsrc_cli.run("dump-manifest", "--update", "--only-manifest-repo", "--force")

    # 8th: commit and push such Manifest to remote
    run_git(mp, "add", "manifest.yml")
    run_git(mp, "commit", "-m", "new assembly chain of version 1.0")
    run_git(mp, "push", "-u", "origin", "ac_1.0")

    # 9th: adding repos, making them ahead/behind
    # AHEAD
    Path(fp / "new_files.txt").touch()
    run_git(fp, "add", "new_files.txt")
    run_git(fp, "commit", "-m", "adding new changes")
    # run_git(fp, "push", "origin", "master")

    # BEHIND
    Path(bp / "new_files.txt").touch()
    run_git(bp, "add", "new_files.txt")
    run_git(bp, "commit", "-m", "adding new changes")
    run_git(bp, "push", "origin", "master")
    run_git(bp, "reset", "--hard", "HEAD~1")

    # BEHIND
    Path(el / "new_files.txt").touch()
    run_git(el, "add", "new_files.txt")
    run_git(el, "commit", "-m", "adding new changes")
    run_git(el, "push", "origin", "master")
    run_git(el, "reset", "--hard", "HEAD~1")

    # 10th A: in 3 Repos the SHA1 has to be present
    tsrc_cli.run("dump-manifest", "--save-to", "m_1.yml")
    m_file = workspace_path / "m_1.yml"
    if m_file.is_file() is False:
        raise Exception("Manifest file does not exists")
    m = load_manifest_safe_mode(m_file, ManifestsTypeOfData.SAVED)
    count: int = 0
    pattern = re.compile("^[0-9a-f]{40}$")
    for repo in m.get_repos():
        if repo.sha1 and pattern.match(repo.sha1):
            count += 1

    if count != 3:
        raise Exception("mismatch on Manifest SHA1 records")

    # 10th B: same but now turn off sha1
    # now ignore position by not setting SHA1
    tsrc_cli.run("dump-manifest", "--save-to", "m_1_off.yml", "--sha1-off")
    m_file = workspace_path / "m_1_off.yml"
    if m_file.is_file() is False:
        raise Exception("Manifest file does not exists")
    m = load_manifest_safe_mode(m_file, ManifestsTypeOfData.SAVED)
    count = 0
    pattern = re.compile("^[0-9a-f]{40}$")
    for repo in m.get_repos():
        if repo.sha1 and pattern.match(repo.sha1):
            count += 1

    if count != 0:
        raise Exception("mismatch on Manifest SHA1 records")

    # 11th A: same as before but for RAW dump
    tsrc_cli.run("dump-manifest", "--raw", ".", "--save-to", "m_2.yml")
    m_file = workspace_path / "m_2.yml"
    if m_file.is_file() is False:
        raise Exception("Manifest file does not exists")
    m = load_manifest_safe_mode(m_file, ManifestsTypeOfData.SAVED)
    count = 0
    pattern = re.compile("^[0-9a-f]{40}$")
    for repo in m.get_repos():
        if repo.sha1 and pattern.match(repo.sha1):
            count += 1

    if count != 3:
        raise Exception("mismatch on Manifest SHA1 records")

    # 11th B: same but now turn off sha1
    # now ignore position by not setting SHA1
    tsrc_cli.run("dump-manifest", "--raw", ".", "--save-to", "m_2.yml")
    m_file = workspace_path / "m_2.yml"
    if m_file.is_file() is False:
        raise Exception("Manifest file does not exists")
    m = load_manifest_safe_mode(m_file, ManifestsTypeOfData.SAVED)
    count = 0
    pattern = re.compile("^[0-9a-f]{40}$")
    for repo in m.get_repos():
        if repo.sha1 and pattern.match(repo.sha1):
            count += 1

    if count != 3:
        raise Exception("mismatch on Manifest SHA1 records")


def test_create_from_workspace_or_raw__sha1_on(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    (only) Create Manifest (by 'dump-manifest')
    from:
    * Workspace
    * RAW
    while using '--sha1-on' option (force SHA1 information)

    test by loading proper Manifest and counting SHA1 records
    """

    # 1st: create bunch of repos
    git_server.add_repo("repo1-mr")
    git_server.push_file("repo1-mr", "test.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "test.txt")
    git_server.add_repo("repo3")
    git_server.push_file("repo3", "test.txt")
    git_server.add_repo("repo4")
    git_server.push_file("repo4", "test.txt")

    # 2nd: create Manifest repo
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init Workspace
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: create Manifest by '--sha1-on'
    # tsrc_cli.run("dump-manifest")
    tsrc_cli.run("dump-manifest", "--sha1-on")

    # 5th: test by load_manifest and pattern match
    m_file = workspace_path / "manifest.yml"
    if m_file.is_file() is False:
        raise Exception("Manifest file does not exists")
    m = load_manifest_safe_mode(m_file, ManifestsTypeOfData.SAVED)
    count: int = 0
    pattern = re.compile("^[0-9a-f]{40}$")
    for repo in m.get_repos():
        if repo.sha1 and pattern.match(repo.sha1):
            count += 1

    if count != 5:
        raise Exception("mismatch on Manifest SHA1 records")

    # 6th: also test RAW mode
    tsrc_cli.run(
        "dump-manifest", "--raw", ".", "--sha1-on", "--save-to", "raw_manifest.yml"
    )

    raw_m_file = workspace_path / "raw_manifest.yml"
    if raw_m_file.is_file() is False:
        raise Exception("Manifest file does not exists")
    raw_m = load_manifest_safe_mode(raw_m_file, ManifestsTypeOfData.SAVED)
    count = 0
    pattern = re.compile("^[0-9a-f]{40}$")
    for repo in raw_m.get_repos():
        if repo.sha1 and pattern.match(repo.sha1):
            count += 1

    if count != 5:
        raise Exception("mismatch on RAW Manifest SHA1 records")


def test_update__ahead_behind__sha1_on(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Update Deep Manifest (by 'dump-manifest')
    from Workspace:
    * while using '--sha1-on' option
    * ahead/behind status of Repo
    * same with '--sha1-off'

    Note:
    Even if we did not change any Repo,
    writing SHA1 to Manifest update it still.

    Scenario:

    # 1st: create bunch of repos
    # 2nd: create Manifest repo
    # 3rd: init Workspace
    # 4th: create Manifest by '--sha1-on'
    # 5th: test by load_manifest and pattern match
    # 6th: checkout changes to Manifest back
    # 7th: introduce some commits to Repos
    # 8th: adding repos, making them ahead/behind to remote
    # 9th: exact check for proper SHA1 on UPDATE
    # 10th: turn off sha1 again with UPDATE
    """

    # 1st: create bunch of repos
    git_server.add_repo("frontend-proj")
    git_server.push_file("frontend-proj", "frontend-proj.txt")
    git_server.add_repo("backend-proj")
    git_server.push_file("backend-proj", "backend-proj.txt")
    git_server.add_repo("extra-lib")
    git_server.push_file("extra-lib", "extra-lib.txt")

    # 2nd: create Manifest repo
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init Workspace
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: create Manifest by '--sha1-on'
    tsrc_cli.run("dump-manifest", "--update", "--sha1-on")

    # 5th: test by load_manifest and pattern match
    m_file = workspace_path / "manifest" / "manifest.yml"
    if m_file.is_file() is False:
        raise Exception("Manifest file does not exists")
    m = load_manifest_safe_mode(m_file, ManifestsTypeOfData.SAVED)
    count: int = 0
    pattern = re.compile("^[0-9a-f]{40}$")
    for repo in m.get_repos():
        if repo.sha1 and pattern.match(repo.sha1):
            count += 1

    if count != 4:
        raise Exception("mismatch on Manifest SHA1 records")

    # 6th: checkout changes to Manifest back
    mp = Path(workspace_path / "manifest")
    run_git(mp, "checkout", ".")

    # 7th: introduce some commits to Repos
    fp = Path(workspace_path / "frontend-proj")
    Path(fp / "latest-changes.txt").touch()
    run_git(fp, "add", "latest-changes.txt")
    run_git(fp, "commit", "-m", "adding latest changes")
    run_git(fp, "push", "origin", "master")

    bp = Path(workspace_path / "backend-proj")
    Path(bp / "latest-changes.txt").touch()
    run_git(bp, "add", "latest-changes.txt")
    run_git(bp, "commit", "-m", "adding latest changes")
    run_git(bp, "push", "origin", "master")

    el = Path(workspace_path / "extra-lib")
    Path(el / "latest-changes.txt").touch()
    run_git(el, "add", "latest-changes.txt")
    run_git(el, "commit", "-m", "adding latest changes")
    run_git(el, "push", "origin", "master")

    # 8th: adding repos, making them ahead/behind to remote
    # AHEAD
    Path(fp / "new_files.txt").touch()
    run_git(fp, "add", "new_files.txt")
    run_git(fp, "commit", "-m", "adding new changes")
    # run_git(fp, "push", "origin", "master")
    _, fp_sha1 = run_git_captured(fp, "rev-parse", "HEAD", check=False)

    # BEHIND
    Path(bp / "new_files.txt").touch()
    run_git(bp, "add", "new_files.txt")
    run_git(bp, "commit", "-m", "adding new changes")
    run_git(bp, "push", "origin", "master")
    run_git(bp, "reset", "--hard", "HEAD~1")
    _, bp_sha1 = run_git_captured(bp, "rev-parse", "HEAD", check=False)

    # BEHIND
    Path(el / "new_files.txt").touch()
    run_git(el, "add", "new_files.txt")
    run_git(el, "commit", "-m", "adding new changes")
    run_git(el, "push", "origin", "master")
    run_git(el, "reset", "--hard", "HEAD~1")
    _, el_sha1 = run_git_captured(el, "rev-parse", "HEAD", check=False)

    # 9th: exact check for proper SHA1 on UPDATE
    tsrc_cli.run("dump-manifest", "--update")
    m_file = workspace_path / "manifest" / "manifest.yml"
    if m_file.is_file() is False:
        raise Exception("Manifest file does not exists")
    m = load_manifest_safe_mode(m_file, ManifestsTypeOfData.SAVED)
    for repo in m.get_repos():
        if repo.dest == "frontend-proj":
            if repo.sha1 != fp_sha1:
                raise Exception("mismatch on Manifest SHA1 records")
        elif repo.dest == "backend-proj":
            if repo.sha1 != bp_sha1:
                raise Exception("mismatch on Manifest SHA1 records")
        elif repo.dest == "extra-lib":
            if repo.sha1 != el_sha1:
                raise Exception("mismatch on Manifest SHA1 records")
        elif repo.dest == "manifest":
            pass
        else:
            raise Exception("mismatch on Manifest's data")

    # 10th: turn off sha1 again with UPDATE
    tsrc_cli.run("dump-manifest", "--update", "--sha1-off", "--force")
    m_file = workspace_path / "manifest" / "manifest.yml"
    if m_file.is_file() is False:
        raise Exception("Manifest file does not exists")
    m = load_manifest_safe_mode(m_file, ManifestsTypeOfData.SAVED)
    for repo in m.get_repos():
        if repo.dest == "frontend-proj":
            if repo.sha1:
                raise Exception("mismatch on Manifest SHA1 records")
        elif repo.dest == "backend-proj":
            if repo.sha1:
                raise Exception("mismatch on Manifest SHA1 records")
        elif repo.dest == "extra-lib":
            if repo.sha1:
                raise Exception("mismatch on Manifest SHA1 records")
        elif repo.dest == "manifest":
            pass
        else:
            raise Exception("mismatch on Manifest's data")
