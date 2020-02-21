from typing import Optional
from path import Path
import cli_ui as ui

import tsrc
import tsrc.executor


class RemoteSetter(tsrc.executor.Task[tsrc.Repo]):
    def __init__(self, workspace_path: Path) -> None:
        self.workspace_path = workspace_path

    def on_start(self, *, num_items: int) -> None:
        ui.info_2("Configuring remotes")

    def on_failure(self, *, num_errors: int) -> None:
        ui.error("Failed to configure remotes")

    def display_item(self, repo: tsrc.Repo) -> str:
        return repo.src

    def process(self, index: int, count: int, repo: tsrc.Repo) -> None:
        try:
            self.try_process_repo(repo)
        except Exception:
            raise tsrc.Error(repo.src, ":", "Failed to configure remotes")

    def try_process_repo(self, repo: tsrc.Repo) -> None:
        for remote in repo.remotes:
            existing_remote = self.get_remote(repo, remote.name)
            if existing_remote:
                if existing_remote.url != remote.url:
                    self.set_remote(repo, remote)
            else:
                self.add_remote(repo, remote)

    def get_remote(self, repo: tsrc.Repo, name: str) -> Optional[tsrc.Remote]:
        full_path = self.workspace_path / repo.src
        rc, url = tsrc.git.run_captured(
            full_path, "remote", "get-url", name, check=False
        )
        if rc != 0:
            return None
        else:
            return tsrc.Remote(name=name, url=url)

    def set_remote(self, repo: tsrc.Repo, remote: tsrc.Remote) -> None:
        full_path = self.workspace_path / repo.src
        # fmt: off
        ui.info_2(repo.src + ":", "Update remote", ui.reset,
                  ui.bold, remote.name, ui.reset,
                  "to new url:", ui.bold, remote.url)
        # fmt: on
        tsrc.git.run(full_path, "remote", "set-url", remote.name, remote.url)

    def add_remote(self, repo: tsrc.Repo, remote: tsrc.Remote) -> None:
        full_path = self.workspace_path / repo.src
        # fmt: off
        ui.info_2(repo.src + ":", "Add remote",
                  ui.bold, remote.name, ui.reset,
                  ui.brown, "(%s)" % remote.url)
        # fmt: on
        tsrc.git.run(full_path, "remote", "add", remote.name, remote.url)
