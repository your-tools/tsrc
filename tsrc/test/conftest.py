""" Fixtures for tsrc testing. """

from pathlib import Path
from typing import Any, Iterator

import pytest
from cli_ui.tests import MessageRecorder

from tsrc.test.helpers.cli import tsrc_cli  # noqa: F401
from tsrc.test.helpers.git_server import git_server  # noqa: F401
from tsrc.workspace import Workspace


@pytest.fixture()
def tmp_path(tmpdir: Any) -> Path:
    """Convert py.path.Local() to Path() objects."""
    return Path(tmpdir.strpath)


@pytest.fixture
def workspace_path(tmp_path: Path) -> Path:
    res = tmp_path / "work"
    res.mkdir()
    return res


@pytest.fixture
def workspace(workspace_path: Path) -> Workspace:
    return Workspace(workspace_path)


@pytest.fixture()
def message_recorder() -> Iterator[MessageRecorder]:
    res = MessageRecorder()
    res.start()
    yield res
    res.stop()
