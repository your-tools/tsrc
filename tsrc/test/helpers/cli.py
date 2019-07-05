from typing import Any
import os
from path import Path
import pytest

import tsrc.cli.main


class CLI:
    def __init__(self) -> None:
        self.workspace_path = Path(os.getcwd())

    def run(self, *args: str, expect_fail: bool = False) -> None:
        if expect_fail:
            with pytest.raises(tsrc.Error):
                tsrc.cli.main.testable_main(args)
        else:
            tsrc.cli.main.testable_main(args)


@pytest.fixture
def tsrc_cli(workspace_path: Path, monkeypatch: Any) -> CLI:
    monkeypatch.chdir(workspace_path)
    res = CLI()
    return res
