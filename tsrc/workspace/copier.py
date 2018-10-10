from typing import NewType, Tuple
import stat

import ui
from path import Path

import tsrc.executor


Copy = NewType('Copy', Tuple[str, str])


class FileCopier(tsrc.executor.Task[Copy]):
    def __init__(self, workspace_path: Path) -> None:
        self.workspace_path = workspace_path

    def on_start(self, *, num_items: int) -> None:
        ui.info_1("Copying files")

    def on_failure(self, *, num_errors: int) -> None:
        ui.error("Failed to perform the following copies:")

    def display_item(self, item: Copy) -> str:
        src, dest = item
        return "%s -> %s" % (src, dest)

    def process(self, item: Copy) -> None:
        src, dest = item
        ui.info(src, "->", dest)
        try:
            src_path = self.workspace_path / src
            dest_path = self.workspace_path / dest
            if dest_path.exists():
                # Re-set the write permissions on the file:
                dest_path.chmod(stat.S_IWRITE)
            src_path.copy(dest_path)
            # Make sure perms are read only for everyone
            dest_path.chmod(0o10444)
        except Exception as e:
            raise tsrc.Error(str(e))
