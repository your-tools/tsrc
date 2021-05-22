from pathlib import Path
from typing import List, Optional, Tuple  # noqa

import attr
import cli_ui as ui

import tsrc
import tsrc.executor
import tsrc.git


class BadBranches(tsrc.Error):
    pass


@attr.s(frozen=True)
class RepoAtIncorrectBranchDescription:
    dest = attr.ib()  # type: str
    actual = attr.ib()  # type: str
    expected = attr.ib()  # type: str


class Syncer(tsrc.executor.Task[tsrc.Repo]):
    def __init__(
        self,
        workspace_path: Path,
        *,
        force: bool = False,
        remote_name: Optional[str] = None,
    ) -> None:
        self.workspace_path = workspace_path
        self.bad_branches = []  # type: List[RepoAtIncorrectBranchDescription]
        self.force = force
        self.remote_name = remote_name

    def on_start(self, *, num_items: int) -> None:
        ui.info_1("Synchronizing workspace")

    def on_failure(self, *, num_errors: int) -> None:
        ui.error("Failed to synchronize workspace")

    def display_item(self, repo: tsrc.Repo) -> str:
        return repo.dest

    def process(self, index: int, count: int, repo: tsrc.Repo) -> None:
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

    def check_branch(self, repo: tsrc.Repo, repo_path: Path) -> None:
        current_branch = None
        try:
            current_branch = tsrc.git.get_current_branch(repo_path)
        except tsrc.Error:
            raise tsrc.Error("Not on any branch")

        if current_branch and current_branch != repo.branch:
            self.bad_branches.append(
                RepoAtIncorrectBranchDescription(
                    dest=repo.dest, actual=current_branch, expected=repo.branch
                )
            )

    def _pick_remotes(self, repo: tsrc.Repo) -> List[tsrc.Remote]:
        if self.remote_name:
            for remote in repo.remotes:
                if remote.name == self.remote_name:
                    return [remote]
            message = f"Remote {self.remote_name} not found for repository {repo.dest}"
            raise tsrc.Error(message)

        return repo.remotes

    def fetch(self, repo: tsrc.Repo) -> None:
        repo_path = self.workspace_path / repo.dest
        for remote in self._pick_remotes(repo):
            try:
                ui.info_2("Fetching", remote.name)
                cmd = ["fetch", "--tags", "--prune", remote.name]
                if self.force:
                    cmd.append("--force")
                tsrc.git.run(repo_path, *cmd)
            except tsrc.Error:
                raise tsrc.Error(f"fetch from '{remote.name}' failed")

    @staticmethod
    def sync_repo_to_ref(repo_path: Path, ref: str) -> None:
        ui.info_2("Resetting to", ref)
        status = tsrc.git.get_status(repo_path)
        if status.dirty:
            raise tsrc.Error(f"{repo_path} is dirty, skipping")
        try:
            tsrc.git.run(repo_path, "reset", "--hard", ref)
        except tsrc.Error:
            raise tsrc.Error("updating ref failed")

    @staticmethod
    def update_submodules(repo_path: Path) -> None:
        tsrc.git.run(repo_path, "submodule", "update", "--init", "--recursive")

    @staticmethod
    def sync_repo_to_branch(repo_path: Path) -> None:
        ui.info_2("Updating branch")
        try:
            tsrc.git.run(repo_path, "merge", "--ff-only", "@{upstream}")
        except tsrc.Error:
            raise tsrc.Error("updating branch failed")

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
