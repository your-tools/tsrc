import textwrap
from pathlib import Path
from typing import Optional

import cli_ui as ui

from tsrc.errors import Error
from tsrc.executor import Task
from tsrc.git import run_git
from tsrc.repo import Remote, Repo


class Cloner(Task[Repo]):
    """Implement cloning missing repos."""

    def __init__(
        self,
        workspace_path: Path,
        *,
        shallow: bool = False,
        remote_name: Optional[str] = None,
    ) -> None:
        self.workspace_path = workspace_path
        self.shallow = shallow
        self.remote_name = remote_name

    def on_failure(self, *, num_errors: int) -> None:
        ui.error("Failed to clone missing repos")

    def display_item(self, repo: Repo) -> str:
        return repo.dest

    def check_shallow_with_sha1(self, repo: Repo) -> None:
        if not repo.sha1:
            return
        if self.shallow:
            message = textwrap.dedent(
                f"Cannot use --shallow with a fixed sha1 ({repo.sha1})\n"
                "Consider using a tag instead"
            )
            raise Error(message)

    def _choose_remote(self, repo: Repo) -> Remote:
        if self.remote_name:
            for remote in repo.remotes:
                if remote.name == self.remote_name:
                    return remote
            message = (
                f"Remote '{self.remote_name}' not found for repository '{repo.dest}'"
            )
            raise Error(message)

        return repo.remotes[0]

    def clone_repo(self, repo: Repo) -> None:
        """Clone a missing repo.

        Note: must use the correct remote(s) and branch when cloning,
        *and* must reset the repo to the correct state if `tag` or
        `sha1` were set in the manifest configuration.
        """
        repo_path = self.workspace_path / repo.dest
        parent = repo_path.parent
        name = repo_path.name
        parent.mkdir(parents=True, exist_ok=True)
        remote = self._choose_remote(repo)
        remote_name = remote.name
        remote_url = remote.url
        clone_args = ["clone", "--origin", remote_name, remote_url]
        ref = None
        if repo.tag:
            ref = repo.tag
        elif repo.branch:
            ref = repo.branch
        if ref:
            clone_args.extend(["--branch", ref])
        if self.shallow:
            clone_args.extend(["--depth", "1"])
        clone_args.append("--recurse-submodules")
        clone_args.append(name)
        try:
            run_git(parent, *clone_args)
        except Error:
            raise Error("Cloning failed")

    def reset_repo(self, repo: Repo) -> None:
        repo_path = self.workspace_path / repo.dest
        ref = repo.sha1
        if ref:
            ui.info_2("Resetting", repo.dest, "to", ref)
            try:
                run_git(repo_path, "reset", "--hard", ref)
            except Error:
                raise Error("Resetting to", ref, "failed")

    def process(self, index: int, count: int, repo: Repo) -> None:
        ui.info_count(index, count, repo.dest)
        self.check_shallow_with_sha1(repo)
        self.clone_repo(repo)
        self.reset_repo(repo)
