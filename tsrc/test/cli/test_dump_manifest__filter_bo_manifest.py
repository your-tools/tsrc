"""
Dump Manifest: filter by:
* considering only Manifest Repo ('--only-manifest')
* disregarding other then Manifest Repo ('--skip-manifest')

* test if '--only-manifest' fails when no Workspace is there
* same for '--skip-manifest'

* test if it disregard using '--skip-manifest' and '--only-manifest' at the same time
"""

from pathlib import Path
from typing import List

# import pytest
import ruamel.yaml
from cli_ui.tests import MessageRecorder

from tsrc.manifest import load_manifest
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer
from tsrc.workspace_config import WorkspaceConfig

"""
=================================
'--skip-manifest' section follows
"""


def test_skip_manifest__on_raw(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Description:
    Test if '--skip-manifest' is respected when
    on RAW dump

    Scenario:
    * 1st: Create repositories
    * 2nd: add Manifest repository
    * 3rd: init workspace on master
    * 4th: RAW dump, while skipping manifest
    * 5th: test if 'manifest' repository is not present
    """
    # 1st: Create repositories
    git_server.add_repo("repo1-mr")
    git_server.push_file("repo1-mr", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "test.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: RAW dump, while skipping manifest
    tsrc_cli.run("dump-manifest", "--raw", ".", "--skip-manifest")

    # 5th: test if 'manifest' repository is not present
    m_path = workspace_path / "manifest.yml"
    m = load_manifest(m_path)
    for repo in m.get_repos():
        if repo.dest == "manifest":
            raise Exception("Manifest should not be included")


def test_skip_manifest__on_workspace(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Description:
    Test if '--skip-manifest' is respected when
    dump from Workspace (no UPDATE)

    Scenario:
    * 1st: Create repositories
    * 2nd: add Manifest repository
    * 3rd: init workspace on master
    * 4th: dump manifest, while skipping DM
    * 5th: test if 'manifest' repository is not present
    """
    # 1st: Create repositories
    git_server.add_repo("repo1-mr")
    git_server.push_file("repo1-mr", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "test.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: dump manifest, while skipping DM
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--skip-manifest")
    assert message_recorder.find(r"=> Creating NEW file 'manifest\.yml'")
    assert message_recorder.find(r":: Dump complete")

    # 5th: test if 'manifest' repository is not present
    m_path = workspace_path / "manifest.yml"
    m = load_manifest(m_path)
    for repo in m.get_repos():
        if repo.dest == "manifest":
            raise Exception("Manifest should not be included")


def test_skip_manifest__on_workspace__on_update(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Description:
    Test if '--skip-manifest' is respected when
    dump from Workspace no UPDATE

    Scenario:
    * 1st: Create repositories
    * 2nd: add Manifest repository
    * 3rd: init workspace on master
    * 4th: change dest of Manifest Repo in Manifest file
    * 5th: dump manifest, while skipping DM
    * 6th: verify if Manifest's dest was not updated
    """
    # 1st: Create repositories
    git_server.add_repo("repo1-mr")
    git_server.push_file("repo1-mr", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "test.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: change dest of Manifest Repo in Manifest file
    dm_path_file = workspace_path / "manifest" / "manifest.yml"
    ad_hoc_update_manifest_repo_dest(dm_path_file)

    # 5th: dump manifest, while skipping DM
    tsrc_cli.run("dump-manifest", "--update", "--skip-manifest", "--force")

    # 6th: verify if Manifest's dest was not updated
    w_m_path = workspace_path / "manifest" / "manifest.yml"
    m = load_manifest(w_m_path)
    for repo in m.get_repos():
        if repo.dest == "manifest":
            raise Exception("Manifest should not be updated")


def ad_hoc_update_manifest_repo_dest(
    manifest_path: Path,
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())

    for _, value in parsed.items():
        if isinstance(value, List):
            for x in value:
                if isinstance(x, ruamel.yaml.comments.CommentedMap):
                    if "dest" in x and x["dest"] == "manifest":
                        x["dest"] = "manifest_x"

    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)


"""
=================================
'--only-manifest' section follows
"""


def test_if_stop_on_mutually_exclusive(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Description:
    Test if it stops when using mutually exclusive options:
    '--skip-manifest' and '--only-manifest' at the same time

    Scenario:
    * 1st: Create repositories
    * 2nd: add Manifest repository
    * 3rd: init workspace on master
    * 4th: test conflicting options
    """
    # 1st: Create repositories
    git_server.add_repo("repo1-mr")
    git_server.push_file("repo1-mr", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "test.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: test conflicting options
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--only-manifest", "--skip-manifest")
    assert message_recorder.find(
        r"Error: '--skip-manifest' and '--only-manifest' are mutually exclusive"
    )


def test_only_manifest__on_workspace(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Description:
    Test if '--only-manifest' is respected when
    dump from Workspace (no UPDATE)

    Scenario:
    * 1st: Create repositories
    * 2nd: add Manifest repository
    * 3rd: init workspace on master
    * 4th: dump manifest, while only considering DM
    * 5th: test if 'manifest' is only Repo in Manifest
    """
    # 1st: Create repositories
    git_server.add_repo("repo1-mr")
    git_server.push_file("repo1-mr", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "test.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: dump manifest, while only considering DM
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--only-manifest")
    assert message_recorder.find(r"=> Creating NEW file 'manifest\.yml'")
    assert message_recorder.find(r":: Dump complete")

    # 5th: test if 'manifest' is only Repo in Manifest
    m_path = workspace_path / "manifest.yml"
    m = load_manifest(m_path)
    count: int = 0
    for repo in m.get_repos():
        if repo.dest == "manifest":
            count += 1
        if repo.dest == "repo1-mr" or repo.dest == "repo2":
            raise Exception("There should be only Manifest")
    if count != 1:
        raise Exception("Manifest processing error")
    print("DEBUG PATH =", workspace_path)


def test_only_manifest__on_raw(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Description:
    Test if '--skip-manifest' is respected when
    on RAW dump

    Scenario:
    * 1st: Create repositories
    * 2nd: add Manifest repository
    * 3rd: init workspace on master
    * 4th: RAW dump, while we are interrestend only in manifest's Repo
    * 5th: test if 'manifest' is only Repo in Manifest
    """
    # 1st: Create repositories
    git_server.add_repo("repo1-mr")
    git_server.push_file("repo1-mr", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "test.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: RAW dump, while we are interrestend only in manifest's Repo
    tsrc_cli.run("dump-manifest", "--raw", ".", "--only-manifest")

    # 5th: test if 'manifest' is only Repo in Manifest
    m_path = workspace_path / "manifest.yml"
    m = load_manifest(m_path)
    count: int = 0
    for repo in m.get_repos():
        if repo.dest == "manifest":
            count += 1
        if repo.dest == "repo1-mr" or repo.dest == "repo2":
            raise Exception("There should be only Manifest")
    if count != 1:
        raise Exception("Manifest processing error")


def test_only_manifest__on_update(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Description:

    'dump-manifest':
    test option '--only-manifest' when Workspace dump on UPDATE

    Scenario:

    # 1st: Create repositories
    # 2nd: add Manifest repository
    # 3rd: init workspace on master
    # 4th: change dest of Manifest Repo in Manifest file
    # 5th: change dest of 'repo2' in Manifest file
    # 6th: dump-manifest, only manifest, UPDATE existin DM
    # 7th: test by load_manifest
    """

    # 1st: Create repositories
    git_server.add_repo("repo1-mr")
    git_server.push_file("repo1-mr", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "test.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: change dest of Manifest Repo in Manifest file
    dm_path_file = workspace_path / "manifest" / "manifest.yml"
    ad_hoc_update_manifest_repo_dest(dm_path_file)

    # 5th: change dest of 'repo2' in Manifest file
    ad_hoc_update_manifest_update_repo2_dest(dm_path_file)

    # 6th: dump-manifest, only manifest, UPDATE existin DM
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--update", "--only-manifest", "--force")
    assert message_recorder.find(r"=> UPDATING Deep Manifest on")
    assert message_recorder.find(r":: Dump complete")

    # 7th: test by load_manifest
    #   there are Repo's that should and sould not be there
    w_m_path = workspace_path / "manifest" / "manifest.yml"
    m = load_manifest(w_m_path)
    count: int = 0
    for repo in m.get_repos():
        if repo.dest == "manifest":
            count += 1
        if repo.dest == "repo2_x":
            count += 2
        if repo.dest == "repo2":  # it should not be there
            raise Exception("Manifest should not be updated back to repo2")
    if count != 3:
        raise Exception("Manifest update error")


def ad_hoc_update_manifest_update_repo2_dest(
    manifest_path: Path,
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())

    for _, value in parsed.items():
        if isinstance(value, List):
            for x in value:
                if isinstance(x, ruamel.yaml.comments.CommentedMap):
                    if "dest" in x and x["dest"] == "repo2":
                        x["dest"] = "repo2_x"

    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)
