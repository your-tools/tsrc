"""
special case when some Repo end up 'dirty'
right after successful sync
"""

import os
from pathlib import Path
from typing import List

# import pytest
import ruamel.yaml
from cli_ui.tests import MessageRecorder

from tsrc.errors import Error
from tsrc.git import run_git
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer
from tsrc.workspace_config import WorkspaceConfig


def test_dirty_after_sync__case_1(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    test unusual case when some Repo may end up with
    '(dirty)' flag right after the successful 'sync'

    in this CASE_1:
    we just let it dirty
    """
    # 1st: Create repository
    backend_path: Path = workspace_path / "main-proj-backend"
    git_server.add_repo("main-proj-backend")
    git_server.push_file("main-proj-backend", "CMakeLists.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: introduce '.gitignore' to root
    with open(backend_path / ".gitignore", "a") as gir:
        gir.write(".*\n")
        gir.write("data\n")
    run_git(backend_path, "add", "-f", ".gitignore")
    run_git(backend_path, "commit", "-m", "introducing root gitignore")
    run_git(backend_path, "push")

    # 5th: ready next version
    run_git(backend_path, "checkout", "-b", "dev")
    #   update '.gitignore'
    with open(backend_path / ".gitignore", "a") as gir:
        gir.write("test.txt\n")
    run_git(backend_path, "add", "-f", ".gitignore")
    #   throw there file not under the version control
    with open(backend_path / "test.txt", "a") as tf:
        tf.write("dummy text")

    #   "data" directory
    os.mkdir(backend_path / "data")
    with open(backend_path / "data" / ".gitignore", "a") as gif:
        gif.write("*\n")
        gif.write(".*")
    new_add: Path = Path("data") / ".gitignore"
    run_git(backend_path, "add", "-f", str(new_add))
    run_git(backend_path, "commit", "-m", "introducing gitignore on data")
    run_git(backend_path, "push", "-u", "origin", "dev")

    #   "extra-data", not in version control
    os.mkdir(backend_path / "data" / "extra-data")
    with open(backend_path / "data" / "extra-data" / "dummy-file.txt", "a") as duf:
        duf.write("just a dummy")

    #   update Manifest file, add, commit, push
    manifest_path = workspace_path / "manifest"
    ad_hoc_update_dm_repo_branch_only(workspace_path)
    run_git(manifest_path, "checkout", "-b", "cmp-1")
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "new cmp-1 branch")
    run_git(manifest_path, "push", "-u", "origin", "cmp-1")

    """
    we are now ready sync forward and than back
    by this, we will invoke the state when right after the
    'sync' the Repo 'main-proj-backend' will end up with 'dirty'
    GIT status.
    """

    # 6th: change branch forward and back
    #   ready change forward (to 'cmp-1')
    tsrc_cli.run("manifest", "--branch", "cmp-1")
    tsrc_cli.run("sync")

    #   and back to 'master'
    tsrc_cli.run("manifest", "--branch", "master")
    tsrc_cli.run("sync")

    # 7th: check the dirty flag
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* main-proj-backend \[ master \]  master \(dirty\)")

    if Path(backend_path / "data" / "extra-data" / "dummy-file.txt").is_file() is False:
        raise Error("ignored file was cleaned. that is not good")


def test_dirty_after_sync__case_2(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    test unusual case when some Repo may end up with
    '(dirty)' flag right after the successful 'sync'

    in this CASE_2:
    clean 'sync' - but ignored files should stay there
    """
    # 1st: Create repository
    backend_path: Path = workspace_path / "main-proj-backend"
    git_server.add_repo("main-proj-backend")
    git_server.push_file("main-proj-backend", "CMakeLists.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: introduce '.gitignore' to root
    with open(backend_path / ".gitignore", "a") as gir:
        gir.write(".*\n")
        gir.write("data\n")
    run_git(backend_path, "add", "-f", ".gitignore")
    run_git(backend_path, "commit", "-m", "introducing root gitignore")
    run_git(backend_path, "push")

    # 5th: ready next version
    run_git(backend_path, "checkout", "-b", "dev")
    #   update '.gitignore'
    with open(backend_path / ".gitignore", "a") as gir:
        gir.write("test.txt\n")
    run_git(backend_path, "add", "-f", ".gitignore")
    #   throw there file not under the version control
    with open(backend_path / "test.txt", "a") as tf:
        tf.write("dummy text")

    #   "data" directory
    os.mkdir(backend_path / "data")
    with open(backend_path / "data" / ".gitignore", "a") as gif:
        gif.write("*\n")
        gif.write(".*")
    new_add: Path = Path("data") / ".gitignore"
    run_git(backend_path, "add", "-f", str(new_add))
    run_git(backend_path, "commit", "-m", "introducing gitignore on data")
    run_git(backend_path, "push", "-u", "origin", "dev")

    #   "extra-data", not in version control
    os.mkdir(backend_path / "data" / "extra-data")
    with open(backend_path / "data" / "extra-data" / "dummy-file.txt", "a") as duf:
        duf.write("just a dummy")

    #   update Manifest file, add, commit, push
    manifest_path = workspace_path / "manifest"
    ad_hoc_update_dm_repo_branch_only(workspace_path)
    run_git(manifest_path, "checkout", "-b", "cmp-1")
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "new cmp-1 branch")
    run_git(manifest_path, "push", "-u", "origin", "cmp-1")

    """
    we are now ready sync forward and than back
    by this, we will invoke the state when right after the
    'sync' the Repo 'main-proj-backend' will end up with 'dirty'
    GIT status.
    """

    # 6th: change branch forward and back
    #   ready change forward (to 'cmp-1')
    tsrc_cli.run("manifest", "--branch", "cmp-1")
    tsrc_cli.run("sync")

    #   and back to 'master'
    tsrc_cli.run("manifest", "--branch", "master")
    tsrc_cli.run("sync", "--clean")

    # 7th: dirty flag should not be there
    message_recorder.reset()
    tsrc_cli.run("status")
    assert not message_recorder.find(
        r"\* main-proj-backend \[ master \]  master \(dirty\)"
    )
    assert message_recorder.find(r"\* main-proj-backend \[ master \]  master")

    if Path(backend_path / "data" / "extra-data" / "dummy-file.txt").is_file() is False:
        raise Error("ignored file was cleaned. that is not good")


def test_dirty_after_sync__case_3(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    test unusual case when some Repo may end up with
    '(dirty)' flag right after the successful 'sync'

    in this CASE_3:
    clean 'sync' ALSO clean ignored files
    """
    # 1st: Create repository
    backend_path: Path = workspace_path / "main-proj-backend"
    git_server.add_repo("main-proj-backend")
    git_server.push_file("main-proj-backend", "CMakeLists.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: introduce '.gitignore' to root
    with open(backend_path / ".gitignore", "a") as gir:
        gir.write(".*\n")
        gir.write("data\n")
    run_git(backend_path, "add", "-f", ".gitignore")
    run_git(backend_path, "commit", "-m", "introducing root gitignore")
    run_git(backend_path, "push")

    # 5th: ready next version
    run_git(backend_path, "checkout", "-b", "dev")
    #   update '.gitignore'
    with open(backend_path / ".gitignore", "a") as gir:
        gir.write("test.txt\n")
    run_git(backend_path, "add", "-f", ".gitignore")
    #   throw there file not under the version control
    with open(backend_path / "test.txt", "a") as tf:
        tf.write("dummy text")

    #   "data" directory
    os.mkdir(backend_path / "data")
    with open(backend_path / "data" / ".gitignore", "a") as gif:
        gif.write("*\n")
        gif.write(".*")
    new_add: Path = Path("data") / ".gitignore"
    run_git(backend_path, "add", "-f", str(new_add))
    run_git(backend_path, "commit", "-m", "introducing gitignore on data")
    run_git(backend_path, "push", "-u", "origin", "dev")

    #   "extra-data", not in version control
    os.mkdir(backend_path / "data" / "extra-data")
    with open(backend_path / "data" / "extra-data" / "dummy-file.txt", "a") as duf:
        duf.write("just a dummy")

    #   update Manifest file, add, commit, push
    manifest_path = workspace_path / "manifest"
    ad_hoc_update_dm_repo_branch_only(workspace_path)
    run_git(manifest_path, "checkout", "-b", "cmp-1")
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "new cmp-1 branch")
    run_git(manifest_path, "push", "-u", "origin", "cmp-1")

    """
    we are now ready sync forward and than back
    by this, we will invoke the state when right after the
    'sync' the Repo 'main-proj-backend' will end up with 'dirty'
    GIT status.
    """

    # 6th: change branch forward and back
    #   ready change forward (to 'cmp-1')
    tsrc_cli.run("manifest", "--branch", "cmp-1")
    tsrc_cli.run("sync")

    #   and back to 'master'
    tsrc_cli.run("manifest", "--branch", "master")
    tsrc_cli.run("sync", "--hard-clean")

    # 7th: dirty flag should not be there
    message_recorder.reset()
    tsrc_cli.run("status")
    assert not message_recorder.find(
        r"\* main-proj-backend \[ master \]  master \(dirty\)"
    )
    assert message_recorder.find(r"\* main-proj-backend \[ master \]  master")

    if Path(backend_path / "data" / "extra-data" / "dummy-file.txt").is_file() is True:
        raise Error("not cleaned properly, ignored file is still there")


def ad_hoc_update_dm_repo_branch_only(
    workspace_path: Path,
) -> None:
    """change Repo's branch only
    so we will be able to introduce change for next 'sync'
    """
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
                        if x["dest"] == "manifest":
                            x["branch"] = "cmp-1"
    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)
