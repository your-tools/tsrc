"""
test_dump_manifest

all tests regarding 'dump_manifest' command

OVERVIEW of tests (1st: option(s), 2nd: fn_name, 3rd: additional description):

--raw   --workspace --preview
    test_raw_dump__workspace__combined_path
    how does it end when --workspace and --raw is provided

--raw   --update"
    test_raw_on_update__check_for_remotes__warning
    test if Warning is printed even ater UPDATE is completed

--raw   --preview
    test_raw_dump_preview
    testing ‘--preview’

--raw   --update-on
    test_raw_dump_update_on
    updating DM file in the Workspace (provided by hand)

--raw   --update
    test_raw_dump_update__use_workspace__without_workspace
    test if it skip non-existant DM, Warning should be displayed

--raw   --update    --force
    test_raw_dump_update_with_multi_remotes__by_load_manifest
    test: Update on ‘remotes’

--raw   --update    --save-to   --no-repo-delete
    test_raw_dump_update_with_multi_remotes__save_to__by_load_manifest
    test if we can update and save to another file, while keeping original
    Manifest intact

--raw
    test_raw_dump_1_repo_no_workspace__deep_path
    COMMON PATH calculation test for 1 Repo

--raw
    test_raw_dump_2_repos_no_workspace__deep_path
    COMMON PATH calculation test for 2 Repos (there may be difference on calculation)

--raw
    test_raw_dump__point_blank__no_luck
    point black range on Repo, should FAIL

--raw
    test_raw_dump_1_repo_no_workspace__long_input_path
    long Path on input on '--raw’

--raw   --save-to
    test_raw_dump_save_to
    test SAVE_TO option

=== === === Workspace only

--update
    test_update_update__by_status
    test: update update: all: add, del, update

--update
    test_on_update
    test actual update on Workspace (using 'status')

--update
    test_on_update__check_for_remotes__after_update_is_ok
    test if UPDATE adds remote(s) if there are none in the current Manifest

--update
    test_on_update__check_for_remotes__is_ok
    test warning about Manifest not useful (when no remote is found)
"""

import os
import re
from pathlib import Path
from shutil import move
from typing import List, Optional, Tuple

# import pytest
import ruamel.yaml
from cli_ui.tests import MessageRecorder

from tsrc.git import run_git
from tsrc.manifest import Manifest, load_manifest, load_manifest_safe_mode
from tsrc.manifest_common_data import ManifestsTypeOfData
from tsrc.repo import Repo
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer
from tsrc.test.helpers.message_recorder_ext import MessageRecorderExt
from tsrc.workspace_config import WorkspaceConfig


def test_raw_dump_save_to(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    test RAW dump and '--save-to' option

    Scenario:

    * 1st: create dir with sub-dir in it
    * 2nd: create 'repo 1', GIT init, add, commit
    * 3rd: RAW dump with different --save-to path
    * 4th: verify last command output
    """
    # 1st: create dir with sub-dir in it
    sub1_path = os.path.join("common path lvl1", "level 2")
    os.makedirs(sub1_path)

    # 2nd: create 'repo 1', GIT init, add, commit
    os.chdir(sub1_path)
    sub1_1_path = Path("repo 1")
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)
    full1_path: Path = Path(os.path.join(workspace_path, sub1_path, sub1_1_path))
    run_git(full1_path, "init")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full1_path, "add", "in_repo.txt")
    run_git(full1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")

    # 3rd: RAW dump with different --save-to path
    os.chdir(workspace_path)
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--raw", "common path lvl1", "--save-to", sub1_path)

    # 4th: verify last command output
    assert message_recorder.find(
        r":: Checking Path \(recursively\) for Repos from: common path lvl1"
    )
    assert message_recorder.find(r"=> Found 1 Repos out of 1 possible paths")
    assert message_recorder.find(
        r"=> Creating NEW file 'common path lvl1.level 2.manifest.yml'"
    )
    assert message_recorder.find(r":: Dump complete")


def test_raw_dump_1_repo_no_workspace__long_input_path(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    similar than 'test_raw_dump_1_repo_no_workspace__deep_path'

    here we provide long path for RAW option to dump from

    Scenario:

    * 1st: create dir with sub-dir in it
    * 2nd: create 'repo 1', GIT init, add, commit
    * 3rd: call: RAW dump on ==> deep path <==
    * 4th: verify that everything goes ok
    """

    # 1st: create dir with sub-dir in it
    sub1_path = os.path.join("common path lvl1", "level 2")
    os.makedirs(sub1_path)

    # 2nd: create 'repo 1', GIT init, add, commit
    os.chdir(sub1_path)
    sub1_1_path = Path("repo 1")
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)
    full1_path: Path = Path(os.path.join(workspace_path, sub1_path, sub1_1_path))
    run_git(full1_path, "init")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full1_path, "add", "in_repo.txt")
    run_git(full1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")

    # 3rd: call: RAW dump on deep path
    os.chdir(workspace_path)
    message_recorder.reset()
    raw_from_str = os.path.join(".", "common path lvl1", "level 2")
    tsrc_cli.run("dump-manifest", "--raw", raw_from_str)

    # 4th: verify that everything goes ok
    assert message_recorder.find(
        r"Warning: No remote found for: 'repo 1' \(path: 'common path lvl1.*level 2.*repo 1'\)"
    )
    assert message_recorder.find(r"=> Found 1 Repos out of 1 possible paths")
    assert message_recorder.find(
        r"=> Creating NEW file 'common path lvl1.*level 2.*manifest.yml'"
    )
    assert message_recorder.find(
        r"Warning: This Manifest is not useful due to some missing remotes"
    )
    assert message_recorder.find(r":: Dump complete")

    # 5th: verify by 'load_manifest_safe_mode'
    m_file = workspace_path / sub1_path / "manifest.yml"
    if m_file.is_file() is False:
        raise Exception("Manifest file does not exists")
    m = load_manifest_safe_mode(m_file, ManifestsTypeOfData.SAVED)
    count: int = 0
    for repo in m.get_repos():
        if repo.dest == "repo 1":
            count += 1
        else:
            raise Exception("Manifest contain wrong item")
    if count != 1:
        raise Exception("Manifest does not contain all items")


def test_of_calculation_common_path_only(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Check calculation of COMMON PATH:

    * test of cut-down from longer path to shorter
    * test of cutting down sub-dir due to mutual mismatch
    * do not fall to '.' COMMON PATH

    Scenario:

    * 1st: init (empty) Workspace
    * 2nd: place various new Repos to various sub-directories
    * 3rd: test mismatch cut-down of COMMON PATH
    * 4th: new Repo that should cut-down due to shorter Path
    * 5th: test COMMON PATH now
    """

    # 1st: init (empty) Workspace
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 2nd: place various new Repos to various sub-directories
    ad_hoc_place_repo_on_path(
        workspace_path,
        Path("a_sub" + os.sep + "a_sub_sub" + os.sep + "a_sub_sub_sub"),
        "repo_a",
    )
    ad_hoc_place_repo_on_path(
        workspace_path,
        Path("a_sub" + os.sep + "a_sub_sub" + os.sep + "b_sub_sub_sub"),
        "repo_b",
    )

    # 3rd: test mismatch cut-down of COMMON PATH
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--raw", ".")
    if os.name == "nt":
        assert message_recorder.find(
            r"=> Using Repo\(s\) COMMON PATH on: '.*\\a_sub\\a_sub_sub.*'"
        )
    else:
        assert message_recorder.find(
            r"=> Using Repo\(s\) COMMON PATH on: '.*"
            + os.sep
            + "a_sub"
            + os.sep
            + "a_sub_sub'"
        )

    # 4th: new Repo that should cut-down due to shorter Path
    ad_hoc_place_repo_on_path(
        workspace_path, Path("a_sub" + os.sep + "b_sub_sub"), "repo_c"
    )

    # 5th: test COMMON PATH now
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--raw", ".")
    if os.name == "nt":
        assert message_recorder.find(r"=> Using Repo\(s\) COMMON PATH on: '.*a_sub'")
    else:
        assert message_recorder.find(
            r"=> Using Repo\(s\) COMMON PATH on: '." + os.sep + "a_sub'"
        )


def ad_hoc_place_repo_on_path(
    workspace_path: Path, repo_path: Path, repo_name: str
) -> None:
    os.makedirs(repo_path)
    os.chdir(repo_path)
    sub1_1_path = Path(repo_name)
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)
    full1_path: Path = Path(os.path.join(workspace_path, repo_path, sub1_1_path))
    run_git(full1_path, "init")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full1_path, "add", "in_repo.txt")
    run_git(full1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")

    os.chdir(workspace_path)


def test_raw_dump_from_abs_path(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Test if COMMON PATH and Current PATH is handled properly
    Which one will be checked needs to be decided >>BEFORE<<
    it gets checked, so we do not end up with unnecessary
    Error about file already exists

    Scenario:

    * 1st: create deep path
    * 2nd: create some repos there
    * 3rd: add Manifest repository there
    * 4th: init workspace (in sub-dir of 2nd level) on master
    * 5th: create different sub-dir (from original root dir)
    * 6th: create 'repo 3', GIT init, add, commit
    * 7th: creates Manifest dump from Workspace to default location
    * 8th: creates RAW Manifest dump to COMMON PATH
    * 9th: now when trying to dump Manifest from Workspace it should fail
    * 10th: move already created Manifest to free default file-name
    * 11th: now it should create successfully
    * 12th: now RAW dump should fail as file in COMMON PATH already exists
    * 13th: if we move "repo 3", than COMMON PATH calculation will
    """
    # 1st: create deep path
    sub1_path = os.path.join("common path lvl1", "level 2")
    os.makedirs(sub1_path)
    os.chdir(sub1_path)

    # 2nd: create some repos there
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "test.txt")
    manifest_url = git_server.manifest_url

    # 3rd: add Manifest repository there
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 4th: init workspace (in sub-dir of 2nd level) on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / sub1_path / ".tsrc" / "config.yml")

    # 5th: create different sub-dir (from original root dir)
    os.chdir(workspace_path)
    sub2_path = os.path.join("common path lvl1")
    os.chdir(sub2_path)

    # 6th: create 'repo 3', GIT init, add, commit
    sub2_1_path = Path("repo 3")
    os.mkdir(sub2_1_path)
    os.chdir(sub2_1_path)
    full2_path: Path = Path(os.path.join(workspace_path, sub2_path, sub2_1_path))
    run_git(full2_path, "init")
    sub2_1_1_file = Path("in_repo.txt")
    sub2_1_1_file.touch()
    run_git(full2_path, "add", "in_repo.txt")
    run_git(full2_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")

    # 7th: creates Manifest dump from Workspace to default location
    os.chdir(workspace_path)
    tsrc_cli.run("dump-manifest", "--workspace", sub1_path)

    # 8th: creates RAW Manifest dump to COMMON PATH
    #   using absolute path for a change
    message_recorder.reset()
    dump_raw_path = os.path.join(workspace_path, sub2_path)
    tsrc_cli.run("dump-manifest", "--raw", dump_raw_path)
    assert message_recorder.find(
        r"=> Creating NEW file '.*common path lvl1.*manifest\.yml'"
    )

    # 9th: now when trying to dump Manifest from Workspace it should fail
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--workspace", sub1_path)
    assert message_recorder.find(
        r"Error: such file 'manifest.yml' already exists, use '--force' to overwrite it"
    )

    # 10th: move already created Manifest to free default file-name
    os.rename("manifest.yml", "old-manifest.yml")

    # 11th: now it should create successfully
    #   this checks if previous RAW dump does not interfere
    #   with Workspace dump
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--workspace", sub1_path)
    assert message_recorder.find(r"=> Creating NEW file 'manifest.yml'")

    # 12th: now RAW dump should fail as file in COMMON PATH already exists
    tsrc_cli.run("dump-manifest", "--raw", ".")
    assert message_recorder.find(
        r"Error: Such file '.*common path lvl1.*manifest\.yml' already exists, use '--force' if you want to overwrite it"
    )

    # 13th: if we move "repo 3", than COMMON PATH calculation will
    #   differ. and that allows saving Manifest to different location
    #   where there is no Manifest with default name
    move(str(workspace_path / sub2_path / sub2_1_path), str(workspace_path / sub1_path))
    tsrc_cli.run("dump-manifest", "--raw", ".")
    assert message_recorder.find(
        # r"=> Creating NEW file '.*common path lvl1.*level 2.*manifest\.yml'"
        r"=> Creating NEW file '.*manifest\.yml'"
    )


def test_raw_dump__point_blank__no_luck(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    test if it is possible to RAW dump Manifest
    from point blank range, meaning from exact place
    where Repo is.

    Something like this is not possible yet.
    In theory we can take previous directory name
    and use it as 'dest' and save manifest also there.

    But that is bad choice. If you want, you can
    change directory to previous one and try dump-manifest
    from there.

    Scenario:

    * 1st: init GIT repository in the root of given directory
    * 2nd: add and commit single file there
    * 3rd: let us see what 'dump-manifest' in RAW grab of current directory will say
    """
    # 1st: init GIT repository in the root of given directory
    run_git(workspace_path, "init")

    # 2nd: add and commit single file there
    thisfile = Path("this_file.txt")
    thisfile.touch()
    run_git(workspace_path, "add", "this_file.txt")
    run_git(workspace_path, "commit", "-m", "adding this_file.txt")

    # 3rd: let us see what 'dump-manifest' in RAW grab of current directory will say
    #   with how it is now working, it should fail
    #   and report no Repos found
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--raw", ".")
    assert message_recorder.find(r"=> No Repos were found")
    assert message_recorder.find(r"Error: cannot obtain data: no Repos were found")


def test_raw_dump__workspace__combined_path(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    test if '--workspace <Path>' is respected when
    RAW dump path is relatvie (not absolute)

    Scenario:

    * 1st: create dir with sub-dir in it
    * 2nd: create 'repo 1', GIT init, add, commit
    * 3rd: go back to original Path, Dump from there
    * 4th: test if '--workspace' gets combined with RAW dump path
    """

    # 1st: create dir with sub-dir in it
    sub1_path = os.path.join("common path lvl1", "level 2")
    os.makedirs(sub1_path)

    # 2nd: create 'repo 1', GIT init, add, commit
    os.chdir(sub1_path)
    sub1_1_path = Path("repo 1")
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)
    full1_path: Path = Path(os.path.join(workspace_path, sub1_path, sub1_1_path))
    run_git(full1_path, "init")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full1_path, "add", "in_repo.txt")
    run_git(full1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")

    # 3rd: go back to original Path, Dump from there
    os.chdir(workspace_path)
    message_recorder.reset()
    tsrc_cli.run(
        "dump-manifest",
        "--raw",
        "level 2",
        "--workspace",
        "common path lvl1",
        "--preview",
    )

    # 4th: test if '--workspace' gets combined with RAW dump path
    assert message_recorder.find(
        r":: Checking Path \(recursively\) for Repos from: .*common path lvl1.*level 2"
    )
    assert message_recorder.find(
        r"=> Using Repo\(s\) COMMON PATH on: '.*common path lvl1.*level 2'"
    )
    test_path_1: str = os.path.join(sub1_path, "repo 1")
    assert message_recorder.find(
        r"Warning: No remote found for: 'repo 1' \(path: '.*common path lvl1.*level 2.*repo 1.*'\)"
    )
    assert message_recorder.find(r"dest: repo 1")


def test_raw_dump_2_repos_no_workspace__deep_path(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    verify if common_path is properly calculated
    when Repos are on deep path

    Scenario:

    * 1st: create dir with sub-dir in it
    * 2nd: create 'repo 1', GIT init, add, commit
    * 3rd: create 'repo 2', GIT init, add, commit
    * 4th: in previous root, call: RAW dump on '.'
    * 5th: check the further output of commnad
    * 6th: verify by 'load_manifest_safe_mode'
    """

    # 1st: create dir with sub-dir in it
    sub1_path = os.path.join("common path lvl1", "level 2")
    os.makedirs(sub1_path)

    # 2nd: create 'repo 1', GIT init, add, commit
    os.chdir(sub1_path)
    sub1_1_path = Path("repo 1")
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)
    full1_path: Path = Path(os.path.join(workspace_path, sub1_path, sub1_1_path))
    run_git(full1_path, "init")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full1_path, "add", "in_repo.txt")
    run_git(full1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")

    # 3rd: create 'repo 2', GIT init, add, commit
    os.chdir(workspace_path)
    os.chdir(sub1_path)
    sub1_2_path = Path("repo 2")
    os.mkdir(sub1_2_path)
    os.chdir(sub1_2_path)
    full2_path: Path = Path(os.path.join(workspace_path, sub1_path, sub1_2_path))
    run_git(full2_path, "init")
    sub1_2_1_file = Path("in_repo.txt")
    sub1_2_1_file.touch()
    run_git(full2_path, "add", "in_repo.txt")
    run_git(full2_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")

    # 4th: in previous root, call: RAW dump on '.'
    os.chdir(workspace_path)
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--raw", ".")

    # 5th: check the further output of commnad
    #   includes checking COMMON PATH
    #   and Warning about missing remotes
    assert message_recorder.find(
        r"=> Using Repo\(s\) COMMON PATH on: '\..*common path lvl1.*level 2'"
    )

    assert message_recorder.find(
        r"Warning: No remote found for: 'repo 1' \(path: 'common path lvl1.*level 2.*repo 1'\)"
    )
    assert message_recorder.find(
        r"Warning: No remote found for: 'repo 2' \(path: 'common path lvl1.*level 2.*repo 2'\)"
    )
    assert message_recorder.find(r"=> Found 2 Repos out of 2 possible paths")
    assert message_recorder.find(
        r"=> Creating NEW file 'common path lvl1.*level 2.*manifest.yml'"
    )
    assert message_recorder.find(
        r"Warning: This Manifest is not useful due to some missing remotes"
    )
    assert message_recorder.find(r":: Dump complete")

    # 6th: verify by 'load_manifest_safe_mode'
    m_file = workspace_path / sub1_path / "manifest.yml"
    m = load_manifest_safe_mode(m_file, ManifestsTypeOfData.SAVED)
    count: int = 0
    for repo in m.get_repos():
        if repo.dest == "repo 1":
            count += 1
        elif repo.dest == "repo 2":
            count += 2
        else:
            raise Exception("Manifest contain wrong item")
    if count != 3:
        raise Exception("Manifest does not contain all items")


def test_raw_dump_1_repo_no_workspace__deep_path(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    verify if just 1 Repo can be properly dumped
    to Manifest without tsrc Workspace at all
    when Repo is on deep path

    test shows that when using just 1 Repo it is different
    when using more Repos, thus we also need to check for
    just 1 Repo

    Scenario:

    * 1st: create dir with sub-dir in it
    * 2nd: create 'repo 1' dir
    * 3rd: GIT: init, add, commit
    * 4th: in previous root, call: RAW dump on '.'
    * 5th: check COMMON PATH and "No remotes" Warning
    * 6th: verify by 'load_manifest_safe_mode'
    """

    # 1st: create dir with sub-dir in it
    sub1_path = os.path.join("common path lvl1", "level 2")
    os.makedirs(sub1_path)

    # 2nd: create 'repo 1' dir
    os.chdir(sub1_path)
    sub1_1_path = Path("repo 1")
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)

    # 3rd: GIT: init, add, commit
    full1_path: Path = Path(os.path.join(workspace_path, sub1_path, sub1_1_path))
    run_git(full1_path, "init")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full1_path, "add", "in_repo.txt")
    run_git(full1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")

    # 4th: in previous root, call: RAW dump on '.'
    os.chdir(workspace_path)
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--raw", ".")

    # 5th: check COMMON PATH and "No remotes" Warning
    assert message_recorder.find(
        r"=> Using Repo\(s\) COMMON PATH on: '\..*common path lvl1.*level 2'"
    )
    assert message_recorder.find(
        r"Warning: No remote found for: 'repo 1' \(path: 'common path lvl1.*level 2.*repo 1'\)"
    )
    assert message_recorder.find(r"=> Found 1 Repos out of 1 possible paths")
    assert message_recorder.find(
        r"=> Creating NEW file 'common path lvl1.*level 2.*manifest.yml'"
    )
    assert message_recorder.find(
        r"Warning: This Manifest is not useful due to some missing remotes"
    )
    assert message_recorder.find(r":: Dump complete")

    # 6th: verify by 'load_manifest_safe_mode'
    m_file = workspace_path / sub1_path / "manifest.yml"
    if m_file.is_file() is False:
        raise Exception("Manifest file does not exists")
    m = load_manifest_safe_mode(m_file, ManifestsTypeOfData.SAVED)
    count: int = 0
    for repo in m.get_repos():
        if repo.dest == "repo 1":
            count += 1
        else:
            raise Exception("Manifest contain wrong item")
    if count != 1:
        raise Exception("Manifest does not contain all items")


def test_raw_dump_update_with_multi_remotes__by_load_manifest(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
) -> None:
    """
    Test how does 'dump-manifest' is able to update
    Manifest repository in the Workspace while using RAW dump.
    Create the worst possible conditions to work with.

    Scenario:

    * 1st: Create repositories (1x multiple remotes)
    * 2nd: add Manifest repository
    * 3rd: init workspace on master
    * 4th: remove "origin" remote from 'manifest/manifest.yml"
    * 5th: remove "upstream" remote from git of Manifest repository
    * 6th: modify Deep Manifest (so update will not be ignored)
    * 7th: test actual RAW dump while updating Manifest repo (use force)
    * 8th: check by loading updated Manifest
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

    # 5th: remove "upstream" remote from git of Manifest repository
    repo1_path = workspace_path / "repo1-mr"
    run_git(repo1_path, "remote", "remove", "upstream")

    # 6th: modify Deep Manifest (so update will not be ignored)
    manifest_file_path = workspace_path / "manifest" / "manifest.yml"
    ad_hoc_insert_repo_item_to_manifest(manifest_file_path, "does_not_matter")

    # 7th: test actual RAW dump while updating Manifest repo (use force)
    tsrc_cli.run("dump-manifest", "--raw", ".", "--update", "--force")

    # 8th: check by loading updated Manifest
    """
    here we have Manifest with wrong remote on 'repo1-mr'
    so the update should check git and obtain the correct remote (name and url)
    and update such data on Manifest. So we should see this state
    when we load the Manifest (by 'load_manifest')
    """
    w_m_path = workspace_path / "manifest" / "manifest.yml"
    m = load_manifest(w_m_path)
    for repo in m.get_repos():
        if repo.dest == "repo1-mr":
            for remote in repo.remotes:
                pattern = re.compile(".*bare.repo1-mr")
                if not (remote.name == "origin" and pattern.match(remote.url)):
                    raise Exception("Wrong repo remotes")


def test_raw_dump_update_with_multi_remotes__save_to__by_load_manifest(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Test how does 'dump-manifest' is able to update
    Manifest repository in the Workspace while using RAW dump.
    Create the worst possible conditions to work with.

    Scenario:

    * 1st: Create repositories (1x multiple remotes)
    * 2nd: add Manifest repository
    * 3rd: init workspace on master
    * 4th: remove "origin" remote from 'manifest/manifest.yml"
    * 5th: remove "upstream" remote from git of Manifest repository
    * 6th: modify Deep Manifest (so update will not be ignored)
    * 7th: test actual RAW dump while updating, but saving to another file
    * 8th: verify no change to original 'manifest/manifest.yml'
    * 9th: verify newly created Manifest: 'new-m.yml'
    """
    # 1st: Create repositories (1x multiple remotes)
    #   'repo1-mr' will have multiple remotes
    repo1_url = git_server.add_repo("repo1-mr")
    git_server.push_file("repo1-mr", "CMakeLists.txt")
    git_server.manifest.set_repo_remotes(
        "repo1-mr",
        [
            ("origin", repo1_url),
            ("upstream", "git@upstream.com"),
            ("debug", "git@debug.com"),
        ],
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

    # 5th: remove "upstream" remote from git of Manifest repository
    repo1_path = workspace_path / "repo1-mr"
    run_git(repo1_path, "remote", "remove", "upstream")

    # 6th: modify Deep Manifest (so update will not be ignored)
    manifest_file_path = workspace_path / "manifest" / "manifest.yml"
    ad_hoc_insert_repo_item_to_manifest(manifest_file_path, "does_not_matter")

    # 7th: test actual RAW dump while updating, but saving to another file
    #   also does not allow Repos to be deleted
    #   * in this case it should not matter if DM is dirty as we are not overwriting it
    #       but instead saving output to another file
    message_recorder.reset()
    tsrc_cli.run(
        "dump-manifest",
        "--raw",
        ".",
        "--update",
        "--save-to",
        "new-m.yml",
        "--no-repo-delete",
    )
    assert message_recorder.find(
        r"=> Creating NEW file 'new-m\.yml' by UPDATING Deep Manifest on 'manifest.manifest\.yml'"
    )

    # 8th: verify no change to original 'manifest/manifest.yml'
    on_8th_point(workspace_path)

    # 9th: verify newly created Manifest: 'new-m.yml'
    #   * verify remotes of 'repo1-mr'
    #   * verify 'repo5' as it should not be deleted
    on_9th_point(workspace_path)


def on_8th_point(workspace_path: Path) -> None:
    found_remote: bool = False
    found_remote_2: bool = False
    w_m_path = workspace_path / "manifest" / "manifest.yml"
    d_m = load_manifest(w_m_path)
    for repo in d_m.get_repos():
        if repo.dest == "repo1-mr":
            for remote in repo.remotes:
                pattern = re.compile(".*bare.repo1-mr")
                if remote.name == "origin" and pattern.match(remote.url):
                    raise Exception("Wrong remote that should not be here")
                if remote.name == "debug" and remote.url == "git@debug.com":
                    found_remote_2 = True
                if remote.name == "upstream" and remote.url == "git@upstream.com":
                    found_remote = True
    if found_remote is False or found_remote_2 is False:
        raise Exception("Wrong repo remotes")


def on_9th_point(workspace_path: Path) -> None:
    n_m_path = workspace_path / "new-m.yml"
    m = load_manifest(n_m_path)
    found_not_deleted: bool = False
    found_remote: bool = False
    found_remote_2: bool = False
    for repo in m.get_repos():
        if repo.dest == "repo1-mr":
            found_remote, found_remote_2 = on_9th_point_on_repo1_mr(repo)

        if repo.dest == "repo5":
            found_not_deleted = True
            if repo.clone_url != "does_not_matter":
                raise Exception("Wrong repo clone_url")

    if found_remote is False or found_remote_2 is False:
        raise Exception("Wrong repo remotes")
    if found_not_deleted is False:
        raise Exception("Missing repo")


def on_9th_point_on_repo1_mr(repo: Repo) -> Tuple[bool, bool]:
    found_remote: bool = False
    found_remote_2: bool = False
    for remote in repo.remotes:
        pattern = re.compile(".*bare.repo1-mr")
        if remote.name == "origin" and pattern.match(remote.url):
            found_remote = True
        if remote.name == "debug" and remote.url == "git@debug.com":
            found_remote_2 = True
        if remote.name == "upstream":
            raise Exception("Wrong remote that should not be here")
    return found_remote, found_remote_2


def test_raw_dump_update__use_workspace__without_workspace(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Check if Workspace gets ignored even if it is called to be used.
    Also check if '--skip-manifest-repo'|'--only-manifest-repo' throws a Warning
    as without Workspace it is not possible to determine Deep Manifest

    Scenario:

    * 1nd: create 'repo 1', GIT init, add, commit
    * 2nd: try to dump manifest by RAW mode, while want to update DM
    * 3rd: test Warning when '--skip-manifest-repo'
    * 4th: test Warning and Error when '--only-manifest-repo'
    """
    # 1nd: create 'repo 1', GIT init, add, commit
    sub1_path = workspace_path
    os.chdir(sub1_path)
    sub1_1_path = Path("repo 1")
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)
    full1_path: Path = Path(os.path.join(workspace_path, sub1_path, sub1_1_path))
    run_git(full1_path, "init", "-b", "master")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full1_path, "add", "in_repo.txt")
    run_git(full1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")

    # 2nd: try to dump manifest by RAW mode, while want to update DM
    #   this should give Warning as there is no Workspace,
    #   nor there is Deep Manifest. in such case, the Workspace
    #   should be ignored, RAW dump should continue without it
    os.chdir(sub1_path)
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--raw", ".", "--update")

    assert message_recorder.find(r"Error: Could not find current workspace")

    # 3rd: test Warning when '--skip-manifest-repo'
    #   without Workspace, we cannot know which is manifest,
    #   thus we cannot skip it. This is just a Warning
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--raw", ".", "--skip-manifest-repo")
    assert message_recorder.find(
        r"Warning: Cannot skip Deep Manifest if there is no Workspace"
    )

    # 4th: test Warning and Error when '--only-manifest-repo'
    #   not only manifest without Workspace can be determined,
    #   there is no data, thus Error is also throwed
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--raw", ".", "--only-manifest-repo", "--force")
    assert message_recorder.find(
        r"Warning: Cannot look for Deep Manifest if there is no Workspace"
    )
    assert message_recorder.find(r"Error: cannot obtain data: no Repos were found")


# flake8: noqa: C901
def ad_hoc_delete_remote_from_manifest(
    manifest_path: Path,
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())

    for _, value in parsed.items():
        if isinstance(value, List):
            for x in value:
                if isinstance(x, ruamel.yaml.comments.CommentedMap):
                    if "dest" in x and x["dest"] == "repo1-mr":
                        if "remotes" in x:
                            idx_to_del: Optional[int] = None
                            remotes = x["remotes"]
                            for idx, _ in enumerate(remotes):
                                if remotes[idx]["name"] == "origin":
                                    idx_to_del = idx
                                    break
                            if isinstance(idx_to_del, int):
                                del remotes[idx_to_del]
                        if "url" in x:
                            del x["url"]

    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)


def test_raw_dump_update_on(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    RAW dump test using '--update-on'
    (we can see the benefits of RAW dump here)

    Scenario:

    * 1st: Create repositories
    * 2nd: add Manifest repository
    * 3rd: init workspace on master
    * 4th: add some other repos, without addit them to Manifest
    * 5th: see that Manifest does not contain latest repos
    * 6th: dump Manifest by RAW dump + '--update-on'
    * 7th: now test how RAW dump updates Manifest
    """

    # 1st: Create repositories
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    git_server.add_repo("repo2")
    git_server.push_file("repo2", "test.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: add some other repos, without addit them to Manifest
    just_clone_repo(
        git_server, workspace_path, "repo3", branch="old_master", add_to_manifest=False
    )
    just_clone_repo(
        git_server, workspace_path, "repo4", branch="old_master", add_to_manifest=False
    )

    # 5th: see that Manifest does not contain latest repos
    message_recorder.reset()
    tsrc_cli.run("status")
    assert not message_recorder.find(r"repo3")
    assert not message_recorder.find(r"repo4")

    # 6th: dump Manifest by RAW dump + '--update-on'
    message_recorder.reset()
    # prepare Deep Manfiest the path
    manifest_path = os.path.join("manifest", "manifest.yml")
    tsrc_cli.run("dump-manifest", "--raw", ".", "--update-on", manifest_path)
    # assert message_recorder.find(f"=> Updating on: '{manifest_path}'")
    assert message_recorder.find(r"=> UPDATING 'manifest.manifest\.yml'")

    # 7th: now test how RAW dump updates Manifest
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(
        r"\* manifest \[ master     \]= master \(dirty\) ~~ MANIFEST"
    )
    assert message_recorder.find(r"\+ repo4    \[ old_master \]  old_master")
    assert message_recorder.find(r"\+ repo3    \[ old_master \]  old_master")
    assert message_recorder.find(r"\* repo2    \[ master     \]  master")
    assert message_recorder.find(r"\* repo1    \[ master     \]  master")


def test_raw_dump_preview(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder_ext: MessageRecorderExt,
) -> None:
    """
    Real test of dumping manifest from RAW Repos (no Workspace)
    Testing feature: '--preview'

    Scenario:

    * 1st: clone repos without init of Workspace
    * 2nd: call RAW dump using preview mode
    * 3rd: verify output using 'find_right_after' feature
    """
    # 1st: clone repos without init of Workspace
    just_clone_repo(git_server, workspace_path, "repo1")
    just_clone_repo(git_server, workspace_path, "repo2")

    # 2nd: call RAW dump using preview mode
    #   in such case Manifest goes to (ui.info) not to file
    message_recorder_ext.reset()
    tsrc_cli.run("dump-manifest", "--raw", ".", "--preview")

    # 3rd: verify output using 'find_right_after' feature
    assert message_recorder_ext.find(r"^repos:$")
    assert message_recorder_ext.find(r"^  - dest: repo1$")
    # "url" may be splitted into 2 lines
    ret = message_recorder_ext.find_right_after(r"^    url: .*bare.repo1$")
    if not ret:
        assert message_recorder_ext.find_right_after(r"^    url:")
        assert message_recorder_ext.find_right_after(r".*bare.repo1$")

    assert message_recorder_ext.find_right_after(r"^    branch: master$")
    assert message_recorder_ext.find(r"^  - dest: repo2$")
    ret = message_recorder_ext.find_right_after(r"^    url: .*bare.repo2$")
    if not ret:
        assert message_recorder_ext.find_right_after(r"^    url:")
        assert message_recorder_ext.find_right_after(r".*bare.repo2$")

    assert message_recorder_ext.find_right_after(r"^    branch: master$")


def just_clone_repo(
    git_server: GitServer,
    workspace_path: Path,
    dest: str,
    branch: str = "master",
    add_to_manifest: bool = True,
) -> None:
    git_server.add_repo(dest, default_branch=branch, add_to_manifest=add_to_manifest)
    git_server.push_file(dest, "CMakeLists.txt", branch=branch)

    repo_url = git_server.get_url(dest)
    run_git(workspace_path, "clone", "-b", branch, repo_url)


"""
(Below) With Workspace Dump (no RAW dump)
"""


def test_update_update__by_status(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    test update_update:
    this means only Repo's items will need update.
    what are these Repo's items?
    * branch
    * tag
    * sha1
    * (remotes is tested in different test)

    NOTE: 'update' will change presence of Repos,
    'update_update' changes Repo's items

    Scenario:

    * 1st: Create repositories
        -    A) test for 'add'
        -    B) test for 'del' (and 'add' SHA1)
        -    C) test for 'update' (updating branch)
    * 2nd: add Manifest repository
    * 3rd: init workspace on master
    * 4th: now let us make some changes on Repo->item level
        -    A) test for 'add'
        -    B) test for 'del' (and 'add' SHA1)
        -    C) test for 'update' (updating branch)
    * 5th: Manifest: checkout to 'snapshot' + tag
    * 6th: do 'dump-manifest' as update
    * 7th: verify 'status'
    """
    # 1st: Create repositories
    #   A) test for 'add'
    git_server.add_repo("repo1", default_branch="main")
    # git_server.change_branch("repo1", "main")
    git_server.push_file("repo1", "CMakeLists.txt", branch="main")
    git_server.tag("repo1", "v1.0", branch="main")

    #   B) test for 'del' (and 'add' SHA1)
    git_server.add_repo("repo2", default_branch="main")

    git_server.push_file("repo2", "test.txt", branch="main")
    repo2_sha1_2 = git_server.get_sha1("repo2")

    git_server.push_file("repo2", "test2.txt", branch="main")
    repo2_sha1_3 = git_server.get_sha1("repo2")

    git_server.push_file("repo2", "test3.txt", branch="main")

    #   C) test for 'update' (updating branch)
    git_server.add_repo("repo3", default_branch="main")
    git_server.push_file("repo3", "test.txt", branch="main")

    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: now let us make some changes on Repo->item level
    # to check how does update_update working

    #   A) test for 'add'
    repo1_path = workspace_path / "repo1"
    run_git(repo1_path, "checkout", "-b", "devel")

    #   B) test for 'del' (and 'add' SHA1)
    repo2_path = workspace_path / "repo2"
    run_git(repo2_path, "checkout", repo2_sha1_2)
    run_git(repo2_path, "checkout", "-b", "middle")
    run_git(repo2_path, "merge", "main")
    run_git(repo2_path, "checkout", repo2_sha1_3)

    #   C) test for 'update' (updating branch)
    repo3_path = workspace_path / "repo3"
    run_git(repo3_path, "checkout", "-b", "point_c")

    # 5th: Manifest: checkout to 'snapshot' + tag
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-b", "snapshot")
    run_git(manifest_path, "tag", "-a", "moded", "-m", "all moded version")
    run_git(manifest_path, "push", "-u", "origin", "snapshot")

    # 6th: do 'dump-manifest' as update
    tsrc_cli.run("dump-manifest", "--update")

    # 7th: verify 'status'
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(
        r"\* repo1    \[ devel on v1.0     \]  devel on v1.0 \(expected: main\) \(missing upstream\)"  # noqa: E501
    )
    # also compare SHA1 hashs
    chck_ptrn = message_recorder.find(
        r"\* repo2    \[ [0-9a-f]{7}           \]  [0-9a-f]{7} \(missing upstream\)"
    )
    pattern = re.compile("^.*repo2.*([0-9a-f]{7}).*([0-9a-f]{7}).*$")
    if chck_ptrn:
        restr = pattern.match(chck_ptrn)
        if not (restr and restr.group(1) == restr.group(2)):
            raise Exception("SHA1 does not match")

    assert message_recorder.find(
        r"\* repo3    \[ point_c           \]  point_c \(expected: main\) \(missing upstream\)"
    )
    assert message_recorder.find(
        r"\* manifest \[ snapshot on moded \]= snapshot on moded \(dirty\) \(expected: master\) ~~ MANIFEST"  # noqa: E501
    )


def test_raw_on_update__check_for_remotes__warning(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    The goal is to hit "not useful Manifest" Warning, when on UPDATE
    We have to use RAW dump here to simulate such Warning. To achieve
    this we need to have some
    Repo that does no have remotes (Grabed) and no remotes found on
    UPDATE source (Deep Manifest) as well. This can only be achieved
    by RAW dump. Thus output Manifest will print Warning.

    Note: this is not possible to hit when on Create from Workspace
    as Workspace does not allow to have missing Remotes

    Scenario:

    * 1st: create bunch of repos
    * 2nd: create Manifest repo
    * 3rd: init Workspace
    * 4th: delete remote from Deep Manifest
    * 5th: check state by 'status'
    * 6th: commit changes to Deep Manifest, so no (dirty)
    * 7th: remove remote 'origin' from local Repo
    * 8th: check 'status', it should report (missing remote) for current Repo state
    * 9th: perform dump Workspace and UPDATE
    * 10th: check if Warning is displayed
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

    # 4th: delete remote from Deep Manifest
    manifest_file_path = workspace_path / "manifest" / "manifest.yml"
    ad_hoc_delete_remote_from_manifest(manifest_file_path)

    # 5th: check state by 'status'
    #   it shourld report '(missing remote)' for Deep Manifest
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* repo1-mr \[ master \(missing remote\) \]  master")
    assert message_recorder.find(r"\* repo2    \[ master                  \]  master")
    assert message_recorder.find(
        r"\* manifest \[ master                  \]= master \(dirty\) ~~ MANIFEST"
    )
    assert message_recorder.find(r"\* repo3    \[ master                  \]  master")
    assert message_recorder.find(r"\* repo4    \[ master                  \]  master")

    # 6th: commit changes to Deep Manifest, so no (dirty)
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "adding repo without url")
    run_git(manifest_path, "push", "-u", "origin", "master")

    # 7th: remove remote 'origin' from local Repo
    repo1_mr_path = workspace_path / "repo1-mr"
    run_git(repo1_mr_path, "remote", "remove", "origin")

    # 8th: check 'status', it should report (missing remote) for current Repo state
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(
        r"\* repo1-mr \[ master \(missing remote\) \]  master \(missing remote\)"
    )

    # 9th: perform dump Workspace and UPDATE
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--raw", ".", "--update")

    # 10th: check if Warning is displayed
    assert message_recorder.find(r"=> UPDATING Deep Manifest on")  # ... path
    assert message_recorder.find(
        r"Warning: This Manifest is not useful due to some missing remotes"
    )
    assert message_recorder.find(r":: Dump complete")


def test_on_update__check_for_remotes__after_update_is_ok(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    The goal is to NOT hit "not useful Manifest" when on UPDATE

    Here we only delete 'url' from Deep Manifest.
    That should gets UPDATEd back, so there should be no Warning

    Scenario:

    * 1st: create bunch of repos
    * 2nd: create Manifest repo
    * 3rd: init Workspace
    * 4th: delete remote from Deep Manifest
    * 5th: check state by 'status'
    * 6th: commit changes to Deep Manifest, so no (dirty)
    * 7th: check 'status', it should report (missing remote) for current Repo state
    * 8th: perform dump Workspace and UPDATE
    * 9th: check if Warning is displayed
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

    # 4th: delete remote from Deep Manifest
    manifest_file_path = workspace_path / "manifest" / "manifest.yml"
    ad_hoc_delete_remote_from_manifest(manifest_file_path)

    # 5th: check state by 'status'
    #   it shourld report '(missing remote)' for Deep Manifest
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"\* repo1-mr \[ master \(missing remote\) \]  master")
    assert message_recorder.find(r"\* repo2    \[ master                  \]  master")
    assert message_recorder.find(
        r"\* manifest \[ master                  \]= master \(dirty\) ~~ MANIFEST"
    )
    assert message_recorder.find(r"\* repo3    \[ master                  \]  master")
    assert message_recorder.find(r"\* repo4    \[ master                  \]  master")

    # 6th: commit changes to Deep Manifest, so no (dirty)
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "adding repo without url")
    run_git(manifest_path, "push", "-u", "origin", "master")

    # 7th: check 'status', it should report (missing remote) for current Repo state
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(
        r"\* manifest \[ master                  \]= master ~~ MANIFEST"
    )

    # 8th: perform dump Workspace and UPDATE
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--update")

    # 9th: check if Warning is displayed
    assert message_recorder.find(r"=> UPDATING Deep Manifest on")  # ... path
    assert not message_recorder.find(
        r"Warning: This Manifest is not useful due to some missing remotes"
    )
    assert message_recorder.find(r":: Dump complete")


def test_on_update__check_for_remotes__is_ok(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    this is successful version of:
    'test_on_update__check_for_remotes__warning'
    just to see if Warning is not printed everytime
    as that will defy other related tests
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

    # 4th: dump Workspace and UPDATE
    message_recorder.reset()
    tsrc_cli.run("dump-manifest", "--update")

    # 5th: what we should not find is Warning
    #   like the one below
    assert not message_recorder.find(
        r"Warning: This Manifest is not useful due to some missing remotes"
    )


def test_on_update(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Test actual outcome of the 'update'

    Scenario:

    * 1st: Create repositories
    * 2nd: add Manifest repository
    * 3rd: init workspace on master
    * 4th: checkout, modify, commit and push Manifest repo to different branch
        so we can keep Manifest with just 3 Repos
    * 5th: add some other repos
    * 6th: sync to update Workspace
        now new repos is cloned to Workspace
    * 7th: Manifest repo: go back to previous branch
        so the current Manifest Repo
        will be different from current statuses of the Workspace.
    * 8th: update current Manifest integrated into Workspace
        calling 'tsrc dump-manifest --update'
    * 9th: check 'status' to know where we stand
        Update:
            * deleting: 'repo5' and 'repo6'
            * updating: 'manifest' (changing branch)
            * adding: 'repo3' and 'repo4'
    """
    # 1st: Create repositories
    git_server.add_repo("repo1")
    git_server.push_file("repo1", "CMakeLists.txt")
    repo2_url = git_server.add_repo("repo2")
    git_server.push_file("repo2", "test.txt")
    manifest_url = git_server.manifest_url

    # 2nd: add Manifest repository
    git_server.add_manifest_repo("manifest")
    git_server.manifest.change_branch("master")

    # 3rd: init workspace on master
    tsrc_cli.run("init", "--branch", "master", manifest_url)
    WorkspaceConfig.from_file(workspace_path / ".tsrc" / "config.yml")

    # 4th: checkout, modify, commit and push Manifest repo to different branch
    manifest_path = workspace_path / "manifest"
    run_git(manifest_path, "checkout", "-B", "old_master")
    manifest_file_path = workspace_path / "manifest" / "manifest.yml"
    ad_hoc_insert_repo_item_to_manifest(manifest_file_path, repo2_url)
    run_git(manifest_path, "add", "manifest.yml")
    run_git(manifest_path, "commit", "-m", "adding repos that does not exists")
    run_git(manifest_path, "push", "-u", "origin", "old_master")

    # 5th: add some other repos
    git_server.add_repo("repo3")
    git_server.push_file("repo3", "test.txt")
    git_server.add_repo("repo4")
    git_server.push_file("repo4", "test.txt")

    # 6th: sync to update Workspace
    tsrc_cli.run("sync")

    # 7th: Manifest repo: go back to previous branch
    run_git(manifest_path, "checkout", "old_master")
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"=> Destination \[Deep Manifest description\]")
    assert message_recorder.find(r"\* repo3                master")
    assert message_recorder.find(r"\* repo4                master")
    assert message_recorder.find(r"\* repo2    \[ master \]  master")
    assert message_recorder.find(r"\* repo1    \[ master \]  master")
    assert message_recorder.find(
        r"\* manifest \[ master \]= old_master \(expected: master\) ~~ MANIFEST"
    )
    assert message_recorder.find(r"- repo5    \[ master \]")
    assert message_recorder.find(r"- repo6    \[ master \]")

    # 8th: update current Manifest integrated into Workspace
    tsrc_cli.run("dump-manifest", "--update")

    # 9th: check 'status' to know where we stand
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(r"=> Destination \[Deep Manifest description\]")
    # no ide what is wrong with below line
    assert message_recorder.find(
        r"\* manifest \[ old_master \]= old_master \(dirty\) \(expected: master\) ~~ MANIFEST"  # noqa: E501
    )
    assert message_recorder.find(r"\* repo4    \[ master     \]  master")
    assert message_recorder.find(r"\* repo2    \[ master     \]  master")
    assert message_recorder.find(r"\* repo1    \[ master     \]  master")
    assert message_recorder.find(r"\* repo3    \[ master     \]  master")


def ad_hoc_insert_repo_item_to_manifest(manifest_path: Path, some_url: str) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())
    for _, value in parsed.items():
        if isinstance(value, List):
            value.append({"dest": "repo5", "url": some_url})
            value.append({"dest": "repo6", "url": some_url})

    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)
