""" Common fixtures for all tests """

import re
import path

import pytest

from tcommon import ui


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
def tmp_path(tmpdir):
    """ Convert py.path.Local() to path.Path() objects """
    return path.Path(tmpdir.strpath)


@pytest.fixture()
def messages(request):
    recorder = MessageRecorder()
    request.addfinalizer(recorder.stop)
    return recorder
