""" Fixtures for tsrc testing """

import path
import pytest

import tsrc.cli.main
import tsrc.git
import tsrc.workspace

from ui.tests.conftest import message_recorder
from .helpers.git_server import git_server
from .helpers.cli import tsrc_cli
from .helpers.push import push_args, repo_path

# silence pyflakes 'unused import' warning
tsrc_cli, git_server, message_recorder, push_args, repo_path


@pytest.fixture()
def tmp_path(tmpdir):
    """ Convert py.path.Local() to path.Path() objects """
    return path.Path(tmpdir.strpath)


@pytest.fixture
def workspace_path(tmp_path):
    return tmp_path.joinpath("work").mkdir()


@pytest.fixture
def workspace(workspace_path):
    return tsrc.workspace.Workspace(workspace_path)
