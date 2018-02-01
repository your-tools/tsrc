import pytest

from tsrc.cli.main import main as tsrc_main
from click.testing import CliRunner


class CLI():
    def __init__(self, workspace_path):
        self.runner = CliRunner()
        self.workspace_path = workspace_path

    def run(self, *args, expect_fail=False):
        print("tsrc", *args)
        result = self.runner.invoke(tsrc_main, args)
        print(result.output)
        exception = result.exception
        if expect_fail:
            assert exception
        else:
            if exception:
                raise exception


@pytest.fixture
def tsrc_cli(workspace_path, monkeypatch):
    monkeypatch.chdir(workspace_path)
    res = CLI(workspace_path)
    return res
