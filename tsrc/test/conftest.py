""" Fixtures for tsrc testing """

from typing import Any
from path import Path
import pytest

import tsrc

from ui.tests.conftest import message_recorder  # noqa
from .helpers.git_server import git_server  # noqa
from .helpers.cli import tsrc_cli  # noqa
from .helpers.push import repo_path, push_args  # noqa


@pytest.fixture()
def tmp_path(tmpdir: Any) -> Path:
    """ Convert py.path.Local() to Path() objects """
    return Path(tmpdir.strpath)


@pytest.fixture
def workspace_path(tmp_path: Path) -> Path:
    return (tmp_path / "work").mkdir()


@pytest.fixture
def workspace(workspace_path: Path) -> tsrc.Workspace:
    return tsrc.Workspace(workspace_path)
