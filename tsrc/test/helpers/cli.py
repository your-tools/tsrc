""" Helper to cal tsrc's main() function.

Used by the `tsrc_cli` fixture.
"""

import os
from pathlib import Path
from typing import Any, Type

import cli_ui as ui
import pytest

import tsrc
import tsrc.cli.main


class CLI:
    def __init__(self) -> None:
        self.workspace_path = Path(os.getcwd())

    def run(self, *args: str) -> None:
        ui.info(">", ui.bold, "tsrc", *args)
        tsrc.cli.main.testable_main(args)

    def run_and_fail(self, *args: str) -> tsrc.Error:
        ui.info(">", ui.bold, "tsrc", *args, end="")
        ui.info(ui.red, " (expecting failure)")
        with pytest.raises(tsrc.Error) as e:
            tsrc.cli.main.testable_main(args)
        return e.value

    def run_and_fail_with(self, error: Type[tsrc.Error], *args: str) -> tsrc.Error:
        actual_error = self.run_and_fail(*args)
        assert isinstance(actual_error, error)
        return actual_error


@pytest.fixture
def tsrc_cli(workspace_path: Path, monkeypatch: Any) -> CLI:
    monkeypatch.chdir(workspace_path)
    res = CLI()
    return res
