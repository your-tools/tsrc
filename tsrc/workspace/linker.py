from typing import List

import cli_ui as ui
from path import Path

import tsrc
import tsrc.executor
import os


class FileLinker(tsrc.executor.Task[tsrc.Link]):
    def __init__(self, workspace_path: Path, repos: List[tsrc.Repo]) -> None:
        self.workspace_path = workspace_path
        self.repos = repos

    def on_start(self, *, num_items: int) -> None:
        ui.info_2("Creating symlinks")

    def on_failure(self, *, num_errors: int) -> None:
        ui.error("Failed to create the following symlinks:")

    def display_item(self, item: tsrc.Link) -> str:
        return f"{item.source} linking to {item.target}"

    def process(self, index: int, count: int, item: tsrc.Link) -> None:
        ui.info_count(index, count, "Linking", item.source, "->", item.target)
        # Both paths are assumed to already be workspace-relative
        source_path = Path(item.source)
        target_path = Path(item.target)
        if source_path.isabs():
            ui.error("Absolute path specified as symlink name:", source_path)
            return
        try:
            full_source = self.workspace_path / item.source
            os.symlink(target_path, full_source, target_path.isdir())
        except Exception as e:
            raise tsrc.Error(str(e))
