import os
import re
import path
import pytest

import tsrc.cli

import ui


class CLI():
    def __init__(self):
        self.workspace_path = path.Path(os.getcwd())

    def run(self, *args, expect_fail=False):
        try:
            tsrc.cli.main.main(args=args)
            rc = 0
        except SystemExit as e:
            rc = e.code
        if expect_fail and rc == 0:
            assert False, "should have failed"
        if rc != 0 and not expect_fail:
            raise SystemExit(rc)


@pytest.fixture
def tsrc_cli(workspace_path, monkeypatch):
    monkeypatch.chdir(workspace_path)
    res = CLI()
    return res
