from pathlib import Path
from typing import List

import cli_ui as ui

from tsrc.executor import Outcome, Task
from tsrc.repo import Repo


class Cleaner(Task[Repo]):
    def __init__(
        self,
        workspace_path: Path,
        *,
        do_hard_clean: bool = False,
    ) -> None:
        self.workspace_path = workspace_path
        self.do_hard_clean = do_hard_clean

    def describe_item(self, item: Repo) -> str:
        return item.dest

    def describe_process_start(self, item: Repo) -> List[ui.Token]:
        return ["Cleaning", item.dest]

    def describe_process_end(self, item: Repo) -> List[ui.Token]:
        return [ui.green, "ok", ui.reset, item.dest]

    def process(self, index: int, count: int, repo: Repo) -> Outcome:
        """
        Clean each repo so it will be ready for next 'sync'
        """
        self.info_count(index, count, "Cleaning", repo.dest)

        repo_path = self.workspace_path / repo.dest
        self.run_git(repo_path, "clean", "-f", "-d")
        if self.do_hard_clean is True:
            self.run_git(repo_path, "clean", "-f", "-X", "-d")

        return Outcome.empty()
