import os
import re
import path
import pytest

from tsrc import ui
import tsrc.cli


class MessageRecorder():
    def __init__(self):
        ui.CONFIG["record"] = True
        ui._MESSAGES = list()

    def stop(self):
        ui.CONFIG["record"] = False
        ui._MESSAGES = list()

    def reset(self):
        ui._MESSAGES = list()

    def find(self, pattern):
        regexp = re.compile(pattern)
        for message in ui._MESSAGES:
            if re.search(regexp, message):
                return message


@pytest.fixture()
def messages(request):
    recorder = MessageRecorder()
    request.addfinalizer(recorder.stop)
    return recorder


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
