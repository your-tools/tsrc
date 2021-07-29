from pathlib import Path

from tsrc.file_system import Copy
from tsrc.git import get_current_branch, run_git, run_git_captured
from tsrc.manifest import Manifest, load_manifest
from tsrc.test.helpers.git_server import GitServer


def read_remote_manifest(workspace_path: Path, git_server: GitServer) -> Manifest:
    run_git(workspace_path, "clone", git_server.manifest_url)
    manifest_yml = workspace_path / "manifest/manifest.yml"
    manifest = load_manifest(manifest_yml)
    return manifest


def test_add_repo_can_clone(workspace_path: Path, git_server: GitServer) -> None:
    """Check that repo added to the GitServer can be cloned,
    typically, they should be bare but not empty!

    """
    foobar_url = git_server.add_repo("foo/bar")
    run_git(workspace_path, "clone", foobar_url)
    assert (workspace_path / "bar").exists()


def test_can_add_copies(workspace_path: Path, git_server: GitServer) -> None:
    git_server.add_repo("foo")
    git_server.manifest.set_file_copy("foo", "foo.txt", "top.txt")
    manifest = read_remote_manifest(workspace_path, git_server)
    assert manifest.file_system_operations == [Copy("foo", "foo.txt", "top.txt")]


def test_add_repo_updates_manifest(workspace_path: Path, git_server: GitServer) -> None:
    git_server.add_repo("foo/bar")
    git_server.add_repo("spam/eggs")
    manifest = read_remote_manifest(workspace_path, git_server)
    repos = manifest.get_repos()
    assert len(repos) == 2
    for repo in repos:
        clone_url = repo.clone_url
        _, out = run_git_captured(workspace_path, "ls-remote", clone_url)
        assert "refs/heads/master" in out


def test_multiple_manifest_branches(
    workspace_path: Path, git_server: GitServer
) -> None:
    git_server.add_repo("foo")
    git_server.manifest.change_branch("devel")
    git_server.add_repo("bar")

    run_git(workspace_path, "clone", git_server.manifest_url)
    manifest_yml = workspace_path / "manifest/manifest.yml"
    manifest = load_manifest(manifest_yml)
    assert len(manifest.get_repos()) == 1

    run_git(workspace_path / "manifest", "reset", "--hard", "origin/devel")
    manifest = load_manifest(manifest_yml)
    assert len(manifest.get_repos()) == 2


def test_push_to_other_branch(workspace_path: Path, git_server: GitServer) -> None:
    foo_url = git_server.add_repo("foo")
    git_server.push_file("foo", "devel.txt", contents="this is devel\n", branch="devel")
    run_git(workspace_path, "clone", foo_url, "--branch", "devel")
    foo_path = workspace_path / "foo"
    assert (foo_path / "devel.txt").read_text() == "this is devel\n"


def test_tag(workspace_path: Path, git_server: GitServer) -> None:
    foo_url = git_server.add_repo("foo")
    git_server.tag("foo", "v0.1", branch="master")
    _, out = run_git_captured(workspace_path, "ls-remote", foo_url)
    assert "refs/tags/v0.1" in out


def test_get_sha1(workspace_path: Path, git_server: GitServer) -> None:
    git_server.add_repo("foo")
    actual = git_server.get_sha1("foo")
    assert type(actual) == str


def test_default_branch_devel(workspace_path: Path, git_server: GitServer) -> None:
    foo_url = git_server.add_repo("foo", default_branch="devel")
    run_git(workspace_path, "clone", foo_url)
    foo_path = workspace_path / "foo"
    cloned_branch = get_current_branch(foo_path)
    assert cloned_branch == "devel"

    manifest = read_remote_manifest(workspace_path, git_server)
    foo_config = manifest.get_repo("foo")
    assert foo_config.branch == "devel"


def test_create_submodule(workspace_path: Path, git_server: GitServer) -> None:
    top_url = git_server.add_repo("top")
    sub_url = git_server.add_repo("sub", add_to_manifest=False)
    git_server.add_submodule("top", url=sub_url, path=Path("sub"))

    run_git(workspace_path, "clone", top_url, "--recurse-submodules")

    top_path = workspace_path / "top"
    sub_readme = top_path / "sub" / "README"
    assert sub_readme.exists()


def test_update_submodule(workspace_path: Path, git_server: GitServer) -> None:
    top_url = git_server.add_repo("top")
    sub_url = git_server.add_repo("sub", add_to_manifest=False)
    git_server.add_submodule("top", url=sub_url, path=Path("sub"))

    run_git(workspace_path, "clone", top_url, "--recurse-submodules")

    git_server.push_file("sub", "new.txt")
    git_server.update_submodule("top", "sub")

    top_path = workspace_path / "top"
    run_git(top_path, "fetch")
    run_git(top_path, "reset", "--hard", "origin/master")
    run_git(top_path, "submodule", "update", "--init", "--recursive")

    new_sub = top_path / "sub" / "new.txt"
    assert new_sub.exists()
