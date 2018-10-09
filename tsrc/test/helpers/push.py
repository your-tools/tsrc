from path import Path
import pytest
from typing import Any
import argparse

from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer


@pytest.fixture
def push_args() -> argparse.Namespace:
    args = argparse.Namespace()
    args.accept = False
    args.assignee = None
    args.close = False
    args.force = False
    args.merge = False
    args.title = None
    args.push_spec = None
    args.ready = False
    args.reviewers = None
    args.target_branch = None
    args.title = None
    args.wip = False
    return args


@pytest.fixture
def repo_path(monkeypatch: Any, git_server: GitServer, tsrc_cli: CLI, workspace_path: Path) -> Path:
    """ Path to a freshly cloned repository """
    git_server.add_repo("owner/project")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    repo_path = workspace_path / "owner/project"
    monkeypatch.chdir(repo_path)
    return repo_path
