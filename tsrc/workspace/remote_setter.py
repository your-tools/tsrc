from pathlib import Path
from typing import Optional

import cli_ui as ui

import tsrc
import tsrc.executor


class RemoteSetter(tsrc.executor.Task[tsrc.Repo]):
    """
    For each repository:

      * look for the remote configured in the manifest,
      * add any missing remote,
      * if a remote is found but with an incorrect URL, update its URL.

    """

    def __init__(self, workspace_path: Path) -> None:
        self.workspace_path = workspace_path

    def on_start(self, *, num_items: int) -> None:
        ui.info_2("Configuring remotes")

    def on_failure(self, *, num_errors: int) -> None:
        ui.error("Failed to configure remotes")

    def display_item(self, repo: tsrc.Repo) -> str:
        return repo.dest

    def process(self, index: int, count: int, repo: tsrc.Repo) -> None:
        for remote in repo.remotes:
            existing_remote = self.get_remote(repo, remote.name)
            if existing_remote:
                if existing_remote.url != remote.url:
                    self.set_remote(repo, remote)
            else:
                self.add_remote(repo, remote)

    def get_remote(self, repo: tsrc.Repo, name: str) -> Optional[tsrc.Remote]:
        full_path = self.workspace_path / repo.dest
        rc, url = tsrc.git.run_captured(
            full_path, "remote", "get-url", name, check=False
        )
        if rc != 0:
            return None
        else:
            return tsrc.Remote(name=name, url=url)

    def set_remote(self, repo: tsrc.Repo, remote: tsrc.Remote) -> None:
        full_path = self.workspace_path / repo.dest
        # fmt: off
        ui.info_3(repo.dest + ":", "Update remote", ui.reset,
                  ui.bold, remote.name, ui.reset,
                  "to new url:", ui.brown, f"({remote.url})")
        # fmt: on
        tsrc.git.run(full_path, "remote", "set-url", remote.name, remote.url)

    def add_remote(self, repo: tsrc.Repo, remote: tsrc.Remote) -> None:
        full_path = self.workspace_path / repo.dest
        # fmt: off
        ui.info_3(repo.dest + ":", "Add remote",
                  ui.bold, remote.name, ui.reset,
                  ui.brown, f"({remote.url})")
        # fmt: on
        tsrc.git.run(full_path, "remote", "add", remote.name, remote.url)
