import argparse
from multiprocessing import cpu_count
from typing import List

import pytest

from tsrc.cli import add_num_jobs_arg, get_num_jobs


class TestNumJobsParsing:
    def parse_args(self, args: List[str]) -> int:
        parser = argparse.ArgumentParser()
        add_num_jobs_arg(parser)
        parsed = parser.parse_args(args)
        return get_num_jobs(parsed)

    def test_defaults_to_all_cpus(self) -> None:
        actual = self.parse_args([])
        assert actual == cpu_count()

    def test_auto_uses_all_cpus(self) -> None:
        actual = self.parse_args(["--jobs", "auto"])
        assert actual == cpu_count()

    def test_specify_num_jobs_explicitly(self) -> None:
        actual = self.parse_args(["--jobs", "3"])
        assert actual == 3

    def test_using_env_variable(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("TSRC_PARALLEL_JOBS", "5")
        actual = self.parse_args([])

        assert actual == 5

    def test_overriding_env_variable_from_command_line(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("TSRC_PARALLEL_JOBS", "5")
        actual = self.parse_args(["--jobs", "6"])

        assert actual == 6
