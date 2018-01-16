import types

import pytest


@pytest.fixture
def push_args():
    args = types.SimpleNamespace()
    args.accept = False
    args.assignee = None
    args.close = False
    args.force = False
    args.merge = False
    args.mr_title = None
    args.push_spec = None
    args.ready = False
    args.reviewers = None
    args.target_branch = "master"
    args.title = None
    args.wip = False
    return args


@pytest.fixture
def repo_path(monkeypatch, git_server, tsrc_cli, workspace_path):
    """ Path to a freshly cloned repository """
    git_server.add_repo("owner/project")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    repo_path = workspace_path.joinpath("owner/project")
    monkeypatch.chdir(repo_path)
    return repo_path
