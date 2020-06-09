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
        return f"{item.dest} linking to {item.src}"

    def process(self, index: int, count: int, item: tsrc.Link) -> None:
        ui.info_count(index, count, "Linking", item.dest, "->", item.src)
        # Both paths are assumed to already be workspace-relative
        src_path = Path(item.src)
        dest_path = Path(item.dest)
        if dest_path.isabs():
            ui.error("Absolute path specified as symlink dest:", dest_path)
            return
        try:
            final_dest = self.workspace_path / item.dest
            os.symlink(src_path, final_dest, src_path.isdir())
        except Exception as e:
            raise tsrc.Error(str(e))
