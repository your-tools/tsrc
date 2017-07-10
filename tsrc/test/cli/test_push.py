from unittest import mock

import pytest

import tsrc.cli.push
import tsrc.git
import tsrc.gitlab

TIMOTHEE = {"name": "Timothee", "id": 1}
THEO = {"name": "Théo Delrieu", "id": 2}
JOHN = {"name": "John", "id": 3}
BART = {"name": "Bart", "id": 4}

MR_STUB = {"id": "3978", "iid": "42", "web_url": "http://mr/42"}


@pytest.fixture
def foo_path(monkeypatch, git_server, tsrc_cli, workspace_path):
    """ Path to a freshly cloned repository """
    git_server.add_repo("foo/bar")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    foo_path = workspace_path.joinpath("foo/bar")
    monkeypatch.chdir(foo_path)


@pytest.fixture
def mock_gl():
    patcher = mock.patch("tsrc.gitlab")
    res = patcher.start()
    res.get_active_users.return_value = [JOHN, BART, TIMOTHEE, THEO]
    res.get_project_id.return_value = "42"
    yield res
    patcher.stop()


def test_creating_merge_request(foo_path, tsrc_cli, mock_gl):
    tsrc.git.run_git(foo_path, "checkout", "-b", "new-feature")
    tsrc.git.run_git(foo_path, "commit", "--message", "new feature", "--allow-empty")

    mock_gl.find_opened_merge_request.return_value = list()
    mock_gl.create_merge_request.return_value = MR_STUB
    tsrc_cli.run("push", "--accept", "--target", "next",
                 "--message", "Best feature ever",
                 "--assignee", "john")
    mock_gl.create_merge_request.assert_called_with("42", "new-feature",
                                                    target_branch="next",
                                                    title="new-feature")
    mock_gl.update_merge_request.assert_called_with(MR_STUB,
                                                    assignee_id=JOHN["id"],
                                                    remove_source_branch=True,
                                                    target_branch="next",
                                                    title="Best feature ever")

    mock_gl.accept_merge_request.assert_called_with(MR_STUB)


def test_existing_merge_request(foo_path, tsrc_cli, mock_gl):
    tsrc.git.run_git(foo_path, "checkout", "-b", "new-feature")
    tsrc.git.run_git(foo_path, "commit", "--message", "new feature", "--allow-empty")

    mock_gl.find_opened_merge_request.return_value = MR_STUB
    tsrc_cli.run("push", "--accept", "--target", "next",
                 "--message", "Best feature ever",
                 "--assignee", "john")

    mock_gl.create_merge_request.assert_not_called()

    mock_gl.update_merge_request.assert_called_with(MR_STUB,
                                                    assignee_id=JOHN["id"],
                                                    remove_source_branch=True,
                                                    target_branch="next",
                                                    title="Best feature ever")


def test_unwipify_existing_merge_request(foo_path, tsrc_cli, mock_gl):
    existing_mr = {
        "title": "WIP: nice title",
        "web_url": "http://example.com/42",
        "iid": "42",
    }
    mock_gl.find_opened_merge_request.return_value = existing_mr

    tsrc_cli.run("push", "--ready")

    mock_gl.create_merge_request.assert_not_called()
    mock_gl.update_merge_request.assert_called_with(existing_mr,
                                                    remove_source_branch=True,
                                                    target_branch="master",
                                                    title="nice title")


def test_wipify_existing_merge_request(foo_path, tsrc_cli, mock_gl):
    existing_mr = {
        "title": "something going on",
        "web_url": "http://example.com/43",
        "iid": "43",
    }
    mock_gl.find_opened_merge_request.return_value = existing_mr

    tsrc_cli.run("push", "--wip")

    mock_gl.create_merge_request.assert_not_called()
    mock_gl.update_merge_request.assert_called_with(existing_mr,
                                                    remove_source_branch=True,
                                                    target_branch="master",
                                                    title="WIP: something going on")


def test_push_force(foo_path, tsrc_cli, mock_gl):
    tsrc.git.run_git(foo_path, "checkout", "-b", "new-feature")
    tsrc.git.run_git(foo_path, "commit", "--message", "one", "--allow-empty")
    tsrc.git.run_git(foo_path, "commit", "--message", "two", "--allow-empty")
    tsrc.git.run_git(foo_path, "push", "origin", "new-feature:new-feature")
    tsrc.git.run_git(foo_path, "reset", "--hard", "HEAD~1")
    tsrc_cli.run("push", "--force")


def test_select_user():
    users = [TIMOTHEE, THEO]
    assert tsrc.cli.push.get_assignee(users, "tim") == TIMOTHEE
    assert tsrc.cli.push.get_assignee(users, "theo") == THEO
    with pytest.raises(tsrc.Error) as e:
        tsrc.cli.push.get_assignee(users, "t")
    print(e.value.message)
    assert "several" in e.value.message
    users = [JOHN, BART]
    with pytest.raises(tsrc.Error) as e:
        tsrc.cli.push.get_assignee(users, "jhon")
    print(e.value.message)
    assert "Did you mean" in e.value.message
