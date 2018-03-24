""" Fixtures for tsrc testing """

from path import Path
import pytest

import tsrc.cli.main
import tsrc.git
import tsrc.workspace

from ui.tests.conftest import message_recorder
from .helpers.git_server import git_server
from .helpers.cli import tsrc_cli
from .helpers.push import repo_path, push_args

# silence pyflakes:
message_recorder, git_server, tsrc_cli, repo_path, push_args


@pytest.fixture()
def tmp_path(tmpdir):
    """ Convert py.path.Local() to Path() objects """
    return Path(tmpdir.strpath)


@pytest.fixture
def workspace_path(tmp_path):
    return tmp_path.joinpath("work").mkdir()


@pytest.fixture
def workspace(workspace_path):
    return tsrc.workspace.Workspace(workspace_path)
