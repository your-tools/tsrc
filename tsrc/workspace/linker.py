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

    # Experiments on symlinks showed the Path status functions
    # of interest behaving as follows:
    #
    #    islink()  exists()    Description
    #    ----------------------------------------------------------
    #    False     False       link_name doesn't currently exist
    #    False     True        link_name corresponds to a file or dir!
    #    True      False       broken symlink, need to remove
    #    True      True        symlink to a valid target, check target name
    #    ----------------------------------------------------------
    #
    # This function returns a boolean indicating whether symlink
    # creation should proceed.
    #
    def check_link(self, link_name: Path, link_target: Path) -> bool:
        remove_link = False
        if link_name.exists() and not link_name.islink():
            raise tsrc.Error("Specified symlink name exists but is not a link")
            return False
        if link_name.islink():
            if not link_name.exists():
                # symlink exists, but points to a non-existent target
                ui.info_3("Replacing broken link")
                remove_link = True
            if link_name.exists():
                # symlink exists and points to some target
                current_target = link_name.readlink()
                if (current_target == link_target):
                    ui.info_3("Leaving existing link")
                    return False
                else:
                    ui.info_3("Replacing existing link")
                    remove_link = True
        if remove_link:
            try:
                os.unlink(link_name)
            except OSError as e:
                raise tsrc.Error(str(e))
        return True

    def process(self, index: int, count: int, item: tsrc.Link) -> None:
        ui.info_count(index, count, "Linking", item.source, "->", item.target)
        # Both paths are assumed to already be workspace-relative
        source_path = Path(item.source)
        target_path = Path(item.target)
        if source_path.isabs():
            raise tsrc.Error("Absolute path specified as symlink name")
        if target_path.isabs():
            raise tsrc.Error("Absolute path specified as symlink target")
        full_source = self.workspace_path / item.source
        make_link = self.check_link(full_source, target_path)
        if make_link:
            try:
                os.symlink(target_path, full_source, target_path.isdir())
            except OSError as e:
                raise tsrc.Error(str(e))
