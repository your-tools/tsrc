import types
import mock

import pytest

import tsrc.cli.push
import tsrc.git
import tsrc.gitlab

GITLAB_URL = "http://gitlab.example.com"
TIMOTHEE = {"name": "timothee", "id": 1}
THEO = {"name": "theo", "id": 2}
JOHN = {"name": "john", "id": 3}
BART = {"name": "bart", "id": 4}

MR_STUB = {"id": "3978", "iid": "42", "web_url": "http://mr/42", "title": "Boring title"}

PROJECT_IDS = {
    "foo/bar": "42"
}


@pytest.fixture
def foo_path(monkeypatch, git_server, tsrc_cli, workspace_path):
    """ Path to a freshly cloned repository """
    git_server.manifest.configure_gitlab(url=GITLAB_URL)
    git_server.add_repo("foo/bar")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    foo_path = workspace_path.joinpath("foo/bar")
    monkeypatch.chdir(foo_path)


@pytest.fixture
def push_args():
    args = types.SimpleNamespace()
    args.accept = False
    args.target_branch = "master"
    args.mr_title = None
    args.assignee = None
    args.force = False
    args.ready = None
    args.wip = None
    return args


@pytest.fixture
def gitlab_mock():
    all_users = [JOHN, BART, TIMOTHEE, THEO]

    def get_project_members(project_id, query):
        assert project_id in PROJECT_IDS.values()
        return [user for user in all_users if query in user["name"]]

    def get_group_members(group_name, query):
        return [user for user in all_users if query in user["name"]]

    gl_mock = mock.create_autospec(tsrc.gitlab.GitLabHelper, instance=True)
    gl_mock.get_project_members = get_project_members
    gl_mock.get_group_members = get_group_members
    gl_mock.get_project_id = lambda x: PROJECT_IDS[x]
    # Define a few helper methods to make tests nicer to read:
    new_defs = {
        "assert_mr_created": gl_mock.create_merge_request.assert_called_with,
        "assert_mr_not_created": gl_mock.create_merge_request.assert_not_called,
        "assert_mr_updated": gl_mock.update_merge_request.assert_called_with,
        "assert_mr_accepted": gl_mock.accept_merge_request.assert_called_with,
    }
    for name, func in new_defs.items():
        setattr(gl_mock, name, func)
    return gl_mock


def test_creating_merge_request(foo_path, tsrc_cli, gitlab_mock, push_args):
    tsrc.git.run_git(foo_path, "checkout", "-b", "new-feature")
    tsrc.git.run_git(foo_path, "commit", "--message", "new feature", "--allow-empty")

    gitlab_mock.find_opened_merge_request.return_value = list()
    gitlab_mock.create_merge_request.return_value = MR_STUB

    push_args.assignee = "john"
    push_args.target_branch = "next"
    push_args.mr_title = "Best feature ever"

    push_action = tsrc.cli.push.PushAction(push_args, gl_helper=gitlab_mock)

    push_action.main()

    gitlab_mock.assert_mr_created(
        "42", "new-feature",
        target_branch="next",
        title="new-feature"
    )
    gitlab_mock.assert_mr_updated(
        MR_STUB,
        assignee_id=JOHN["id"],
        remove_source_branch=True,
        target_branch="next",
        title="Best feature ever"
    )


def test_existing_merge_request(foo_path, tsrc_cli, gitlab_mock, push_args):
    tsrc.git.run_git(foo_path, "checkout", "-b", "new-feature")
    tsrc.git.run_git(foo_path, "commit", "--message", "new feature", "--allow-empty")

    gitlab_mock.find_opened_merge_request.return_value = MR_STUB

    push_args.target_branch = "next"
    push_args.mr_title = "Best feature ever"
    push_action = tsrc.cli.push.PushAction(push_args, gl_helper=gitlab_mock)
    push_action.main()

    gitlab_mock.assert_mr_not_created()
    gitlab_mock.assert_mr_updated(
        MR_STUB,
        remove_source_branch=True,
        target_branch="next",
        title="Best feature ever"
    )


def test_accept_merge_request(foo_path, tsrc_cli, gitlab_mock, push_args):
    tsrc.git.run_git(foo_path, "checkout", "-b", "new-feature")
    tsrc.git.run_git(foo_path, "commit", "--message", "new feature", "--allow-empty")

    gitlab_mock.find_opened_merge_request.return_value = MR_STUB

    push_args.accept = True
    push_action = tsrc.cli.push.PushAction(push_args, gl_helper=gitlab_mock)
    push_action.main()

    gitlab_mock.assert_mr_accepted(MR_STUB)


def test_unwipify_existing_merge_request(foo_path, tsrc_cli, gitlab_mock, push_args):
    existing_mr = {
        "title": "WIP: nice title",
        "web_url": "http://example.com/42",
        "iid": "42",
    }
    gitlab_mock.find_opened_merge_request.return_value = existing_mr

    push_args.ready = True
    push_action = tsrc.cli.push.PushAction(push_args, gl_helper=gitlab_mock)
    push_action.main()

    gitlab_mock.assert_mr_not_created()
    gitlab_mock.assert_mr_updated(
        existing_mr,
        remove_source_branch=True,
        target_branch="master",
        title="nice title"
    )
