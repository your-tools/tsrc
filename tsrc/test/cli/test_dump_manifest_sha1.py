"""
test SHA1 related manifest dump
like: '--sha1-only'
"""

import re
from pathlib import Path

import pytest
from cli_ui.tests import MessageRecorder

from tsrc.manifest import load_manifest_safe_mode
from tsrc.manifest_common_data import ManifestsTypeOfData
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer
from tsrc.workspace_config import WorkspaceConfig


def test_create_from_workspace__sha1_only(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Create Manifest (by 'dump-manifest')
    from Workspace while using '--sha1-only' option
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

    # 4th: create Manifest by '--sha1-only'
    # tsrc_cli.run("dump-manifest")
    tsrc_cli.run("dump-manifest", "--sha1-only")

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


@pytest.mark.last
def test_update__sha1_only(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Update Deep Manifest (by 'dump-manifest')
    from Workspace while using '--sha1-only' option

    Even if we did not change any Repo,
    writing SHA1 to Manifest update it still.
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

    # 4th: create Manifest by '--sha1-only'
    # tsrc_cli.run("dump-manifest")
    tsrc_cli.run("dump-manifest", "--update", "--sha1-only")

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

    if count != 5:
        raise Exception("mismatch on Manifest SHA1 records")
