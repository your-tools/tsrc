from typing import List
import stat

import cli_ui as ui
from path import Path

import tsrc
import tsrc.executor


class FileCopier(tsrc.executor.Task[tsrc.Copy]):
    def __init__(self, workspace_path: Path, repos: List[tsrc.Repo]) -> None:
        self.workspace_path = workspace_path
        self.repos = repos

    def on_start(self, *, num_items: int) -> None:
        ui.info_2("Copying files")

    def on_failure(self, *, num_errors: int) -> None:
        ui.error("Failed to perform the following copies:")

    def display_item(self, item: tsrc.Copy) -> str:
        return "%s/%s -> %s" % (item.repo, item.src, item.dest)

    def process(self, index: int, count: int, item: tsrc.Copy) -> None:
        known_sources = {x.src for x in self.repos}
        if item.repo not in known_sources:
            return
        ui.info_count(index, count, item.src, "->", item.dest)
        try:
            src_path = self.workspace_path / item.repo / item.src
            dest_path = self.workspace_path / item.dest
            if dest_path.exists():
                # Re-set the write permissions on the file:
                dest_path.chmod(stat.S_IWRITE)
            src_path.copy(dest_path)
            # Make sure perms are read only for everyone
            dest_path.chmod(0o10444)
        except Exception as e:
            raise tsrc.Error(str(e))
