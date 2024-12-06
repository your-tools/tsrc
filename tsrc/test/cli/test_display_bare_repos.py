"""
Test 'status' display with Bare Repo postion

This is in fact extension to DM FM MM test display
"""

import os
from pathlib import Path
from typing import List, Optional

# import pytest
import ruamel.yaml
from cli_ui.tests import MessageRecorder

from tsrc.git import run_git, run_git_captured
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer
from tsrc.test.helpers.message_recorder_ext import MessageRecorderExt
from tsrc.workspace_config import WorkspaceConfig


def test_create_new_assembly_chain_by_tag_and_sha1(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder: MessageRecorder,
) -> None:
    """
    Test when Bare Repo's have Tag and SHA1,
    while it:
    * does not point to the same commit
    * does point to the same commit

    and how does it show in 'status' command
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

    # 4th: introduce some changes to various repositories
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
    run_git(el, "tag", "-a", "ver_x", "-m", "version x")
    _, sha1_of_tag = run_git_captured(el, "rev-parse", "HEAD", check=False)
    run_git(el, "commit", "-m", "adding latest changes")
    run_git(el, "push", "origin", "master")

    # 5th: consider reaching some consistant state, thus
    #   start to create new assembly chain
    #   by checking out new branch on Manifest
    mp = Path(workspace_path / "manifest")
    run_git(mp, "checkout", "-b", "ac_1.0")

    # 6th: create Manifest with SHA1 marks while skipping Manifest Repo
    tsrc_cli.run("dump-manifest", "--sha1-only", "--update", "--skip-manifest")

    # 7th: let us update Manifest, but only with its branch (no SHA1)
    tsrc_cli.run("dump-manifest", "--update", "--only-manifest", "--force")

    tsrc_cli.run("status")

    # 8th: commit and push such Manifest to remote
    run_git(mp, "add", "manifest.yml")
    run_git(mp, "commit", "-m", "new assembly chain of version 1.0")
    run_git(mp, "push", "-u", "origin", "ac_1.0")

    """
    We have successfully created assembly chain of version 1.0

    Let us now continue with development towards another
    assembly chain
    """

    # 9th: adding more changes to create another assembly chain
    Path(fp / "new_files.txt").touch()
    run_git(fp, "add", "new_files.txt")
    run_git(fp, "commit", "-m", "adding new changes")
    run_git(fp, "push", "origin", "master")

    Path(bp / "new_files.txt").touch()
    run_git(bp, "add", "new_files.txt")
    run_git(bp, "commit", "-m", "adding new changes")
    run_git(bp, "push", "origin", "master")

    Path(el / "new_files.txt").touch()
    run_git(el, "add", "new_files.txt")
    run_git(el, "commit", "-m", "adding new changes")
    run_git(el, "push", "origin", "master")

    # 10th: dumping and updating Manifest
    tsrc_cli.run(
        "dump-manifest", "--raw", ".", "--sha1-only", "--update", "--skip-manifest"
    )

    # checkout new branch for Manifest in order to dump it to Manifest later
    run_git(mp, "checkout", "-b", "ac_1.1")
    tsrc_cli.run("dump-manifest", "--update", "--only-manifest", "--force")
    run_git(mp, "add", "manifest.yml")
    run_git(mp, "commit", "-m", "new assembly chain of version 1.1")
    run_git(mp, "push", "-u", "origin", "refs/heads/ac_1.1")

    # 11th: change branch for next Manifest
    tsrc_cli.run("manifest", "--branch", "ac_1.1")

    """
    We are now ready to sync 'ac_1.1' version
    """

    # 12th: sync the new version
    tsrc_cli.run("sync")

    # 13th: we want to return back to older assembly chain 'ac_1.0'
    tsrc_cli.run("manifest", "--branch", "ac_1.0")

    # 14th: sync the older version
    tsrc_cli.run("sync")

    _, wrong_sha1_of_tag = run_git_captured(el, "rev-parse", "HEAD", check=False)
    ad_hoc_update_sha1_from_manifest(mp / "manifest.yml", wrong_sha1_of_tag)
    ad_hoc_add_tag_to_manifest(mp / "manifest.yml", "ver_x")

    # 15th: we can see here wrong SHA1 for branch+Tag
    message_recorder.reset()
    tsrc_cli.run("status")
    short_wrong_sha1 = wrong_sha1_of_tag[:7]
    assert message_recorder.find(
        rf"\* extra-lib     \[ master on ver_x !! {short_wrong_sha1} \]  master .1 commit"
    )

    # 16th: and now there is correct brach+Tag+SHA1
    ad_hoc_update_sha1_from_manifest(mp / "manifest.yml", sha1_of_tag)
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(
        r"\* extra-lib     \[ master on ver_x .1 commit \]  master .1 commit"
    )


def test_create_new_assembly_chain_by_sha1(
    tsrc_cli: CLI,
    git_server: GitServer,
    workspace_path: Path,
    message_recorder_ext: MessageRecorderExt,
) -> None:
    """
    test various types of temporary bare repos
    displays like:
    * X commits behind
    * missing remote
    * wrong commit

    Scenario (mostly taken from examle:USE-CASE 2):

    * 1st: create repositories representing project
    * 2nd: add there a Manifest Repo
    * 3rd: init Workspace
    * 4th: introduce some changes to various repositories
       simulating development process
    * 5th: consider reaching some consistant state, thus
       start to create new assembly chain
       by checking out new branch on Manifest
    * 6th: create Manifest with SHA1 marks while skipping Manifest Repo
    * 7th: let us update Manifest, but only with its branch (no SHA1)
    * 8th: commit and push such Manifest to remote

    We have successfully created assembly chain of version 1.0

    Let us now continue with development towards another
    assembly chain

    * 9th: adding more changes to create another assembly chain
    * 10th: dumping and updating Manifest
    * 11th: change branch for next Manifest

    We are now ready to sync 'ac_1.1' version

    * 12th: sync the new version
    * 13th: we want to return back to older assembly chain 'ac_1.0'
    * 14th: sync the older version
    * 15th: let us see how it end-up when showing the status

    Now we can see, that all non-Manifest Repositories are
    1 commit behind. That is exactly right as we have synced
    to previous assembly chain. It was on the same branch,
    yet the commit SHA1 was earlier in time
    """
    message_recorder = message_recorder_ext

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

    # 4th: introduce some changes to various repositories
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
    tsrc_cli.run("dump-manifest", "--sha1-only", "--update", "--skip-manifest")

    # 7th: let us update Manifest, but only with its branch (no SHA1)
    tsrc_cli.run("dump-manifest", "--update", "--only-manifest", "--force")

    # 8th: commit and push such Manifest to remote
    run_git(mp, "add", "manifest.yml")
    run_git(mp, "commit", "-m", "new assembly chain of version 1.0")
    run_git(mp, "push", "-u", "origin", "ac_1.0")

    """
    We have successfully created assembly chain of version 1.0

    Let us now continue with development towards another
    assembly chain
    """

    # 9th: adding more changes to create another assembly chain
    Path(fp / "new_files.txt").touch()
    run_git(fp, "add", "new_files.txt")
    run_git(fp, "commit", "-m", "adding new changes")
    run_git(fp, "push", "origin", "master")

    Path(bp / "new_files.txt").touch()
    run_git(bp, "add", "new_files.txt")
    run_git(bp, "commit", "-m", "adding new changes")
    run_git(bp, "push", "origin", "master")

    Path(el / "new_files.txt").touch()
    run_git(el, "add", "new_files.txt")
    run_git(el, "commit", "-m", "adding new changes")
    run_git(el, "push", "origin", "master")

    # to test how it will handle repos with located in sub-dir
    sub1_path = Path("inside")
    os.makedirs(sub1_path)
    os.chdir(sub1_path)
    sub1_1_path = Path("repo_inside")
    os.mkdir(sub1_1_path)
    os.chdir(sub1_1_path)
    full1_path: Path = Path(os.path.join(workspace_path, sub1_path, sub1_1_path))
    run_git(full1_path, "init")
    sub1_1_1_file = Path("in_repo.txt")
    sub1_1_1_file.touch()
    run_git(full1_path, "add", "in_repo.txt")
    run_git(full1_path, "commit", "in_repo.txt", "-m", "adding in_repo.txt file")
    # we need to add remote as well
    sub_1_1_url = git_server.get_url(str(sub1_1_path))
    sub_1_1_url_path = Path(git_server.url_to_local_path(sub_1_1_url))
    sub_1_1_url_path.mkdir()
    run_git(sub_1_1_url_path, "init", "--bare")
    run_git(full1_path, "remote", "add", "origin", sub_1_1_url)
    run_git(full1_path, "push", "-u", "origin", "refs/heads/master")

    os.chdir(workspace_path)

    # 10th: dumping and updating Manifest
    tsrc_cli.run(
        "dump-manifest", "--raw", ".", "--sha1-only", "--update", "--skip-manifest"
    )

    # checkout new branch for Manifest in order to dump it to Manifest later
    run_git(mp, "checkout", "-b", "ac_1.1")
    tsrc_cli.run("dump-manifest", "--update", "--only-manifest", "--force")
    run_git(mp, "add", "manifest.yml")
    run_git(mp, "commit", "-m", "new assembly chain of version 1.1")
    run_git(mp, "push", "-u", "origin", "refs/heads/ac_1.1")

    # 11th: change branch for next Manifest
    tsrc_cli.run("manifest", "--branch", "ac_1.1")

    """
    We are now ready to sync 'ac_1.1' version
    """

    # 12th: sync the new version
    tsrc_cli.run("sync")

    # 13th: we want to return back to older assembly chain 'ac_1.0'
    tsrc_cli.run("manifest", "--branch", "ac_1.0")

    # 14th: sync the older version
    tsrc_cli.run("sync")

    # 15th: let us see how it end-up when showing the status
    tsrc_cli.run("status")

    """
    Now we can see, that all non-Manifest Repositories are
    1 commit behind. That is exactly right as we have synced
    to previous assembly chain. It was on the same branch,
    yet the commit SHA1 was earlier in time
    """

    # 16th: checkout yet another new 'dev' branch
    run_git(mp, "checkout", "-b", "dev")
    ad_hoc_delete_remote_from_manifest(mp / "manifest.yml")
    run_git(mp, "commit", "-a", "-m", "'new on branch dev'")
    run_git(mp, "push", "-u", "origin", "refs/heads/dev")

    # 17th: set it for next sync
    tsrc_cli.run("manifest", "--branch", "dev")

    # 18th: set wrong SHA1 that is not present
    _, el_sha1 = run_git_captured(el, "rev-parse", "HEAD")
    transl_s = "abcdef0123456789"
    transl_d = "0123456789abcdef"
    transl_table = str.maketrans(transl_s, transl_d)
    el_wrong_sha1 = el_sha1.translate(transl_table)
    ad_hoc_update_sha1_from_manifest(mp / "manifest.yml", el_wrong_sha1)

    # 19th: now we should see demaged SHA1 marked by "!!"
    message_recorder.reset()
    tsrc_cli.run("status")
    assert message_recorder.find(
        r"\* extra-lib     \[ master !! [0-9a-f]{7}                  \]  \( master .1 commit                   == master \) .1 commit"
    )
    assert message_recorder.find(
        r"\* frontend-proj \[ master \?\? [0-9a-f]{7} \(missing remote\) ]  \( master \?\? [0-9a-f]{7} \(missing remote\) << master \) .1 commit"
    )

    # 20th: extra status test 2 A
    #   here FM leftover should appear
    tsrc_cli.run("manifest", "--branch", "ac_1.1")
    message_recorder.reset()
    tsrc_cli.run("status", "--show-leftovers-status")
    if os.name == "nt":
        assert message_recorder.find(
            r"\+ inside\\repo_inside                                         \( master ~~ commit  == master \)"
        )
    else:
        assert message_recorder.find(
            r"\+ inside"
            + os.sep
            + r"repo_inside                                         \( master ~~ commit  == master \)"
        )

    # 21th: test displaying of FM leftover status
    with open(full1_path / "in_repo.txt", "a") as mod_this_file:
        mod_this_file.write("it is now modified")
    message_recorder.reset()
    tsrc_cli.run("status", "--show-leftovers-status")
    if os.name == "nt":
        assert message_recorder.find(
            r"\+ inside\\repo_inside                                         \( master ~~ commit  << master \) \(dirty\)"
        )
    else:
        assert message_recorder.find(
            rf"\+ inside{os.sep}repo_inside                                         \( master ~~ commit  << master \) \(dirty\)"
        )

    # 22th: extra status test 2 B
    #   even if status of leftover is not displayed,
    #   the '<<' is correct as the repo is dirty, and thus not same
    message_recorder.reset()
    tsrc_cli.run("status")
    if os.name == "nt":
        assert message_recorder.find(
            r"\+ inside\\repo_inside                                         \( master ~~ commit  << master \)"
        )
    else:
        assert message_recorder.find(
            rf"\+ inside{os.sep}repo_inside                                         \( master ~~ commit  << master \)"
        )

    # 23th: extra status test 3:
    #   test comparsion of DM leftover with FM comparsion
    tsrc_cli.run("dump-manifest", "--raw", ".", "--update", "--force")
    message_recorder.reset()
    tsrc_cli.run("status", "--show-leftovers-status")
    if os.name == "nt":
        assert message_recorder.find(
            r"\+ inside\\repo_inside \[ master \]  \( master ~~ commit  << master \) \(dirty\)"
        )
    else:
        assert message_recorder.find(
            rf"\+ inside{os.sep}repo_inside \[ master \]  \( master ~~ commit  << master \) \(dirty\)"
        )

    # 24th: get rid of dirty repo
    run_git(full1_path, "checkout", ".")
    message_recorder.reset()
    tsrc_cli.run("status")
    if os.name == "nt":
        assert message_recorder.find(
            r"\+ inside\\repo_inside \[ master \]  \( master ~~ commit  == master \)"
        )
    else:
        assert message_recorder.find(
            rf"\+ inside{os.sep}repo_inside \[ master \]  \( master ~~ commit  == master \)"
        )
    assert message_recorder.find(
        r"\* backend-proj       \[ master \]  \( master ~~ commit  << master \) .1 commit"
    )


def ad_hoc_add_tag_to_manifest(
    manifest_path: Path,
    this_tag: str,
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())

    for _, value in parsed.items():
        if isinstance(value, List):
            for x in value:
                if isinstance(x, ruamel.yaml.comments.CommentedMap):
                    if "dest" in x and x["dest"] == "extra-lib":
                        x["tag"] = this_tag
    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)


def ad_hoc_update_sha1_from_manifest(
    manifest_path: Path,
    this_sha1: str,
) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())

    for _, value in parsed.items():
        if isinstance(value, List):
            for x in value:
                if isinstance(x, ruamel.yaml.comments.CommentedMap):
                    if "dest" in x and x["dest"] == "extra-lib":
                        if "sha1" in x:
                            x["sha1"] = this_sha1
    # write the file down
    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)


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
                    if "dest" in x and x["dest"] == "frontend-proj":
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
