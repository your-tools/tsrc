from pathlib import Path

from tsrc.cli.env_setter import (
    EnvSetter,
    get_repo_vars,
    get_status_vars,
    get_workspace_vars,
)
from tsrc.git import GitStatus, run_git
from tsrc.repo import Remote, Repo
from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer
from tsrc.workspace import Workspace


def test_set_project_dest_and_branch(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    git_server.add_repo("foo")
    git_server.add_repo("bar", default_branch="devel")

    tsrc_cli.run("init", git_server.manifest_url)
    bar_path = workspace_path / "bar"
    run_git(bar_path, "checkout", "-b", "other")

    workspace = Workspace(workspace_path)
    manifest = workspace.get_manifest()
    env_setter = EnvSetter(workspace)

    workspace_vars = get_workspace_vars(workspace)
    assert workspace_vars["TSRC_MANIFEST_URL"] == git_server.manifest_url
    assert workspace_vars["TSRC_MANIFEST_BRANCH"] == "master"
    assert workspace_vars["TSRC_WORKSPACE_PATH"] == str(workspace_path)

    foo_repo = manifest.get_repo("foo")
    foo_env = env_setter.get_env_for_repo(foo_repo)
    # check that shared env is part of the result for foo
    assert foo_env["TSRC_MANIFEST_URL"] == git_server.manifest_url
    assert foo_env["TSRC_PROJECT_CLONE_URL"] == foo_repo.clone_url

    # check that bar and foo envs are different
    bar_repo = manifest.get_repo("bar")
    bar_env = env_setter.get_env_for_repo(bar_repo)
    assert bar_env["TSRC_PROJECT_DEST"] == "bar"
    assert bar_env["TSRC_PROJECT_MANIFEST_BRANCH"] == "devel"

    # check that git status is set
    assert bar_env["TSRC_PROJECT_STATUS_BRANCH"] == "other"


def test_get_repo_vars() -> None:
    origin = Remote(name="origin", url="git@origin.tld")
    mirror = Remote(name="mirror", url="git@mirror.com")
    foo = Repo(dest="foo", remotes=[origin, mirror], branch="devel")

    actual = get_repo_vars(foo)
    assert actual["TSRC_PROJECT_DEST"] == "foo"
    assert actual["TSRC_PROJECT_MANIFEST_BRANCH"] == "devel"
    assert actual["TSRC_PROJECT_CLONE_URL"] == "git@origin.tld"
    assert actual["TSRC_PROJECT_REMOTE_ORIGIN"] == "git@origin.tld"
    assert actual["TSRC_PROJECT_REMOTE_MIRROR"] == "git@mirror.com"


def test_git_status_vars(tmp_path: Path) -> None:
    git_status = GitStatus(tmp_path)
    git_status.untracked = 0
    git_status.added = 1
    git_status.staged = 2
    git_status.not_staged = 3
    git_status.behind = 4
    git_status.ahead = 5
    git_status.branch = "other"
    git_status.sha1 = "abcde43"
    git_status.tag = "some-tag"
    git_status.dirty = True

    actual = get_status_vars(git_status)

    assert actual["TSRC_PROJECT_STATUS_UNTRACKED"] == "0"
    assert actual["TSRC_PROJECT_STATUS_ADDED"] == "1"
    assert actual["TSRC_PROJECT_STATUS_STAGED"] == "2"
    assert actual["TSRC_PROJECT_STATUS_NOT_STAGED"] == "3"
    assert actual["TSRC_PROJECT_STATUS_BEHIND"] == "4"
    assert actual["TSRC_PROJECT_STATUS_AHEAD"] == "5"
    assert actual["TSRC_PROJECT_STATUS_BRANCH"] == "other"
    assert actual["TSRC_PROJECT_STATUS_SHA1"] == "abcde43"
    assert actual["TSRC_PROJECT_STATUS_TAG"] == "some-tag"
    assert actual["TSRC_PROJECT_STATUS_DIRTY"] == "true"
