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
        full_source = self.workspace_path / item.source
        # Source exists but is not actually a symlink
        if full_source.exists() and not full_source.islink():
            ui.error("Specified symlink name exists but is not a link:", source_path)
            return
        # If source exists as a symlink, check the target
        if full_source.islink():
            if not full_source.exists():
                ui.info_3("Replacing broken link")
                os.unlink(full_source)
            if full_source.exists():
                existing_target = full_source.readlink()
                if (existing_target == target_path):
                    ui.info_3("Leaving existing link")
                    return
                else:
                    ui.info_3("Replacing existing link")
                    os.unlink(full_source)
        try:
            os.symlink(target_path, full_source, target_path.isdir())
        except Exception as e:
            raise tsrc.Error(str(e))
