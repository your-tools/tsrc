from pathlib import Path
from typing import List, Optional

import attr
import cli_ui as ui

from tsrc.errors import Error
from tsrc.executor import Task
from tsrc.git import get_current_branch, get_git_status, run_git
from tsrc.repo import Remote, Repo


class BadBranches(Error):
    pass


@attr.s(frozen=True)
class RepoAtIncorrectBranchDescription:
    dest: str = attr.ib()
    actual: str = attr.ib()
    expected: str = attr.ib()


class Syncer(Task[Repo]):
    def __init__(
        self,
        workspace_path: Path,
        *,
        force: bool = False,
        remote_name: Optional[str] = None,
    ) -> None:
        self.workspace_path = workspace_path
        self.bad_branches: List[RepoAtIncorrectBranchDescription] = []
        self.force = force
        self.remote_name = remote_name

    def on_start(self, *, num_items: int) -> None:
        ui.info_1("Synchronizing workspace")

    def on_failure(self, *, num_errors: int) -> None:
        ui.error("Failed to synchronize workspace")

    def display_item(self, repo: Repo) -> str:
        return repo.dest

    def process(self, index: int, count: int, repo: Repo) -> None:
        """Synchronize a repo given its configuration in the manifest.

        Always start by running `git fetch`, then either:

        * try resetting the repo to the given tag or sha1 (abort
          if the repo is dirty)

        * or try merging the local branch with its upstream (abort if not
          on on the correct branch, or if the merge is not fast-forward).
        """
        ui.info_count(index, count, repo.dest)
        repo_path = self.workspace_path / repo.dest
        self.fetch(repo)
        ref = None

        if repo.tag:
            ref = repo.tag
        elif repo.sha1:
            ref = repo.sha1

        if ref:
            self.sync_repo_to_ref(repo_path, ref)
        else:
            self.check_branch(repo, repo_path)
            self.sync_repo_to_branch(repo_path)

        self.update_submodules(repo_path)

    def check_branch(self, repo: Repo, repo_path: Path) -> None:
        current_branch = None
        try:
            current_branch = get_current_branch(repo_path)
        except Error:
            raise Error("Not on any branch")

        if current_branch and current_branch != repo.branch:
            self.bad_branches.append(
                RepoAtIncorrectBranchDescription(
                    dest=repo.dest, actual=current_branch, expected=repo.branch
                )
            )

    def _pick_remotes(self, repo: Repo) -> List[Remote]:
        if self.remote_name:
            for remote in repo.remotes:
                if remote.name == self.remote_name:
                    return [remote]
            message = f"Remote {self.remote_name} not found for repository {repo.dest}"
            raise Error(message)

        return repo.remotes

    def fetch(self, repo: Repo) -> None:
        repo_path = self.workspace_path / repo.dest
        for remote in self._pick_remotes(repo):
            try:
                ui.info_2("Fetching", remote.name)
                cmd = ["fetch", "--tags", "--prune", remote.name]
                if self.force:
                    cmd.append("--force")
                run_git(repo_path, *cmd)
            except Error:
                raise Error(f"fetch from '{remote.name}' failed")

    @staticmethod
    def sync_repo_to_ref(repo_path: Path, ref: str) -> None:
        ui.info_2("Resetting to", ref)
        status = get_git_status(repo_path)
        if status.dirty:
            raise Error(f"{repo_path} is dirty, skipping")
        try:
            run_git(repo_path, "reset", "--hard", ref)
        except Error:
            raise Error("updating ref failed")

    @staticmethod
    def update_submodules(repo_path: Path) -> None:
        run_git(repo_path, "submodule", "update", "--init", "--recursive")

    @staticmethod
    def sync_repo_to_branch(repo_path: Path) -> None:
        ui.info_2("Updating branch")
        try:
            run_git(repo_path, "merge", "--ff-only", "@{upstream}")
        except Error:
            raise Error("updating branch failed")

    def display_bad_branches(self) -> None:
        if not self.bad_branches:
            return
        ui.error("Some projects were not on the correct branch")
        headers = ("project", "actual", "expected")
        data = [
            ((ui.bold, x.dest), (ui.red, x.actual), (ui.green, x.expected))
            for x in self.bad_branches
        ]
        ui.info_table(data, headers=headers)
        raise BadBranches()
