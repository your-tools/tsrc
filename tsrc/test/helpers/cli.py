""" Helper to call tsrc's main() function.

Used by the `tsrc_cli` fixture.
"""

import os
from pathlib import Path
from typing import Any, List, Type

import cli_ui as ui
import pytest

from tsrc.cli.main import testable_main
from tsrc.errors import Error


def append_jobs_option(*args: str) -> List[str]:
    jobs = os.environ.get("TSRC_TEST_JOBS")
    if jobs:
        action, *rest = args
        if action not in ["apply-manifest", "version"]:
            return [action, "-j", jobs, *rest]
    return [*args]


class CLI:
    def __init__(self) -> None:
        self.workspace_path = Path(os.getcwd())

    def run(self, *args: str) -> None:
        tsrc_args = append_jobs_option(*args)
        ui.info(">", ui.bold, "tsrc", *tsrc_args)
        testable_main(tsrc_args)

    def run_and_fail(self, *args: str) -> Error:
        jobs = os.environ.get("TSRC_TEST_JOBS")
        if jobs:
            args = [*args, "-j", jobs]  # type: ignore
        ui.info(">", ui.bold, "tsrc", *args, end="")
        ui.info(ui.red, " (expecting failure)")
        with pytest.raises(Error) as e:
            testable_main(args)
        return e.value

    def run_and_fail_with(self, error: Type[Error], *args: str) -> Error:
        actual_error = self.run_and_fail(*args)
        assert isinstance(actual_error, error)
        return actual_error


@pytest.fixture
def tsrc_cli(workspace_path: Path, monkeypatch: Any) -> CLI:
    monkeypatch.chdir(workspace_path)
    res = CLI()
    return res
