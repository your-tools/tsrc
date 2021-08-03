import subprocess
from pathlib import Path

import cli_ui as ui
import pytest

from tsrc.git import DOWN, UP, GitStatus
from tsrc.test.helpers.git_server import BareRepo


class GitProject:
    def __init__(self, path: Path, remote_repo: BareRepo):
        self.path = path
        # Make sure the initial branch is the same regardless of the user
        # git configuration
        self.run_git("init", "--initial-branch", "master")
        self.remote_repo = remote_repo
        self.run_git("remote", "add", "origin", str(remote_repo.path))

    def get_status(self) -> GitStatus:
        status = GitStatus(self.path)
        status.update()
        return status

    def make_initial_commit(self) -> None:
        self.write_file("README", "This is the README")
        self.commit_changes("initial commit")

    def commit_changes(self, message: str) -> None:
        self.run_git("add", ".")
        self.run_git("commit", "-m", message)

    def run_git(self, *cmd: str) -> None:
        subprocess.run(
            ["git", *cmd],
            check=True,
            cwd=self.path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def write_file(self, name: str, contents: str) -> None:
        (self.path / name).write_text(contents)


@pytest.fixture
def git_project(tmp_path: Path, remote_repo: BareRepo) -> GitProject:
    src_path = tmp_path / "src"
    src_path.mkdir(parents=True)
    res = GitProject(src_path, remote_repo)
    return res


@pytest.fixture
def remote_repo(tmp_path: Path) -> BareRepo:
    srv_path = tmp_path / "srv"
    srv_path.mkdir(parents=True)
    return BareRepo.create(srv_path, "master", empty=True)


def test_empty(git_project: GitProject) -> None:
    status = git_project.get_status()
    assert status.empty


def test_clean_on_master(git_project: GitProject) -> None:
    git_project.make_initial_commit()
    actual = git_project.get_status()
    assert actual.branch == "master"


def test_dirty_on_master(git_project: GitProject) -> None:
    git_project.make_initial_commit()
    git_project.write_file("new.txt", "new file")
    actual = git_project.get_status()
    assert actual.dirty


def test_behind_1_commit(git_project: GitProject) -> None:
    git_project.make_initial_commit()
    git_project.run_git("push", "-u", "origin", "master")

    git_project.remote_repo.commit_file(
        "new.txt", branch="master", contents="new", message="add new file"
    )

    git_project.run_git("fetch")

    actual = git_project.get_status()
    assert actual.ahead == 0
    assert actual.behind == 1


def test_ahead_2_commits(git_project: GitProject) -> None:
    git_project.make_initial_commit()
    git_project.run_git("push", "-u", "origin", "master")

    git_project.write_file("first", "This is the first new file")
    git_project.commit_changes("first new file")

    git_project.write_file("second", "This is the second new file")
    git_project.commit_changes("second new file")

    actual = git_project.get_status()
    assert actual.ahead == 2
    assert actual.behind == 0


def test_on_sha1(git_project: GitProject) -> None:
    git_project.make_initial_commit()

    git_project.write_file("first", "This is the first new file")
    git_project.commit_changes("first new file")

    git_project.run_git("checkout", "HEAD~1")

    actual = git_project.get_status()
    assert actual.branch is None
    assert actual.sha1 is not None


def test_on_tag(git_project: GitProject) -> None:
    git_project.make_initial_commit()

    git_project.run_git("tag", "v0.1")

    actual = git_project.get_status()
    assert actual.tag == "v0.1"


class TestDescribe:
    dummy_path = Path("src")

    def test_up_to_date(self) -> None:
        status = GitStatus(self.dummy_path)
        status.branch = "master"
        assert status.describe() == [ui.green, "master", ui.reset]

    def test_ahead_1_commit(self) -> None:
        status = GitStatus(self.dummy_path)
        status.branch = "master"
        status.ahead = 1
        # fmt: off
        assert status.describe() == [
            ui.green, "master", ui.reset,
            ui.blue, f"{UP}1 commit", ui.reset
        ]
        # fmt: on

    def test_diverged(self) -> None:
        status = GitStatus(self.dummy_path)
        status.branch = "master"
        status.ahead = 1
        status.behind = 2
        # fmt: off
        assert status.describe() == [
            ui.green, "master", ui.reset,
            ui.blue, f"{UP}1 commit", ui.reset,
            ui.blue, f"{DOWN}2 commits", ui.reset,
        ]
        # fmt: on

    def test_on_sha1(self) -> None:
        status = GitStatus(self.dummy_path)
        status.sha1 = "b6cfd80"
        assert status.describe() == [ui.red, "b6cfd80", ui.reset]

    def test_on_tag(self) -> None:
        status = GitStatus(self.dummy_path)
        status.tag = "v0.1"
        assert status.describe() == [ui.yellow, "on", "v0.1", ui.reset]
