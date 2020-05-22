from typing import Optional

import textwrap

from path import Path
import cli_ui as ui

import tsrc
import tsrc.git
import tsrc.executor


class Cloner(tsrc.executor.Task[tsrc.Repo]):
    def __init__(
        self, workspace_path: Path, *, shallow: bool = False, remote_name: Optional[str] = None
    ) -> None:
        self.workspace_path = workspace_path
        self.shallow = shallow
        self.remote_name = remote_name

    def on_start(self, *, num_items: int) -> None:
        ui.info_2("Cloning missing repos")

    def on_failure(self, *, num_errors: int) -> None:
        ui.error("Failed to clone missing repos")

    def display_item(self, repo: tsrc.Repo) -> str:
        return repo.src

    def check_shallow_with_sha1(self, repo: tsrc.Repo) -> None:
        if not repo.sha1:
            return
        if self.shallow:
            message = textwrap.dedent(
                "Cannot use --shallow with a fixed sha1 ({repo.sha1})\n"
                "Consider using a tag instead"
            )
            message = message.format(repo=repo)
            raise tsrc.Error(message)

    def _choose_remote(self, repo: tsrc.Repo) -> tsrc.Remote:
        if self.remote_name:
            for remote in repo.remotes:
                if remote.name == self.remote_name:
                    return remote
            message = "Remote {name} not found for repository {source}!"
            message.format(name=self.remote_name, source=repo.src)
            raise tsrc.Error(message)

        return repo.remotes[0]

    def clone_repo(self, repo: tsrc.Repo) -> None:
        repo_path = self.workspace_path / repo.src
        parent, name = repo_path.splitpath()
        parent.makedirs_p()
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
        clone_args.append(name)
        try:
            tsrc.git.run(parent, *clone_args)
        except tsrc.Error:
            raise tsrc.Error("Cloning failed")

    def reset_repo(self, repo: tsrc.Repo) -> None:
        repo_path = self.workspace_path / repo.src
        ref = repo.sha1
        if ref:
            ui.info_2("Resetting", repo.src, "to", ref)
            try:
                tsrc.git.run(repo_path, "reset", "--hard", ref)
            except tsrc.Error:
                raise tsrc.Error("Resetting to", ref, "failed")

    def process(self, index: int, count: int, repo: tsrc.Repo) -> None:
        ui.info_count(index, count, repo.src)
        self.check_shallow_with_sha1(repo)
        self.clone_repo(repo)
        self.reset_repo(repo)
