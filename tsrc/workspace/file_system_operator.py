from pathlib import Path
from typing import List

import cli_ui as ui

from tsrc.errors import Error
from tsrc.executor import Task
from tsrc.file_system import FileSystemOperation
from tsrc.repo import Repo


class FileSystemOperator(Task[FileSystemOperation]):
    """Implement file system operations to be run once every missing
    repo has been cloned, like copying files or creating symlinks.

    """

    def __init__(self, workspace_path: Path, repos: List[Repo]) -> None:
        self.workspace_path = workspace_path
        self.repos = repos

    def on_failure(self, *, num_errors: int) -> None:
        ui.error("Failed to perform the following operations:")

    def display_item(self, item: FileSystemOperation) -> str:
        return str(item)

    def process(self, index: int, count: int, item: FileSystemOperation) -> None:
        ui.info_count(index, count, item)
        try:
            item.perform(self.workspace_path)
        except OSError as e:
            raise Error(str(e))
