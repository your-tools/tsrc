from typing import Any, Callable
import os

from path import Path
import pytest
import cli_ui as ui

import tsrc
import tsrc.cli.main

# This is the type of the `tsrc.Error` class itself.
# it makes sense if you see a class as a callable
# that returns instances of itself
ErrorCtor = Callable[..., tsrc.Error]


class CLI:
    def __init__(self) -> None:
        self.workspace_path = Path(os.getcwd())

    def run(self, *args: str,) -> None:
        ui.info(">", ui.bold, "tsrc", *args)
        tsrc.cli.main.testable_main(args)

    def run_and_fail(self, *args: str) -> tsrc.Error:
        ui.info(">", ui.bold, "tsrc", *args, end="")
        ui.info(ui.red, " (expecting failure)")
        with pytest.raises(tsrc.Error) as e:
            tsrc.cli.main.testable_main(args)
        return e.value  # type: ignore

    def run_and_fail_with(self, error: ErrorCtor, *args: str) -> tsrc.Error:
        ui.info(">", ui.bold, "tsrc", *args, end="")
        ui.info(ui.red, " (expecting failure)")
        with pytest.raises(error) as e:
            tsrc.cli.main.testable_main(args)
        return e.value  # type: ignore


@pytest.fixture
def tsrc_cli(workspace_path: Path, monkeypatch: Any) -> CLI:
    monkeypatch.chdir(workspace_path)
    res = CLI()
    return res
