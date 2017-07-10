from unittest import mock

import pytest

import tsrc.cli.push
import tsrc.git
import tsrc.gitlab

JOHN = {"name": "John", "id": 42}
BART = {"name": "Bart", "id": 33}
TIMOTHEE = {"name": "Timothee", "id": 1}
THEO = {"name": "Théo Delrieu", "id": 2}


@pytest.fixture
def foo_path(monkeypatch, git_server, tsrc_cli, workspace_path):
    """ Path to a freshly cloned repository """
    git_server.add_repo("foo/bar")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    foo_path = workspace_path.joinpath("foo/bar")
    monkeypatch.chdir(foo_path)


def test_create_merge_request(foo_path, tsrc_cli):
    tsrc.git.run_git(foo_path, "checkout", "-b", "new-feature")
    tsrc.git.run_git(foo_path, "commit", "--message", "new feature", "--allow-empty")

    with mock.patch("tsrc.gitlab") as mock_gitlab:
        mock_gitlab.project_name_form_url.return_value = "foo/bar"
        mock_gitlab.get_project_id.return_value = 42
        merge_request_stub = {"web_url": "http://gitlab/mr/42"}
        mock_gitlab.ensure_merge_request.return_value = merge_request_stub
        mock_gitlab.get_active_users.return_value = [JOHN, BART, TIMOTHEE, THEO]

        # By default, it should create a merge request
        tsrc_cli.run("push", "--accept", "--target", "next", "--message", "Best feature ever",
                     "--assignee", "john")
        mock_gitlab.ensure_merge_request.assert_called_with(42, "new-feature",
                                                            target_branch="next",
                                                            title="Best feature ever",
                                                            assignee=JOHN)

        # And with --accept, it should accept the merge request
        mock_gitlab.reset()
        tsrc_cli.run("push", "--accept")
        mock_gitlab.ensure_merge_request.assert_called_with(42, "new-feature",
                                                            target_branch="master",
                                                            title=None, assignee=None)
        mock_gitlab.accept_merge_request.assert_called_with(merge_request_stub)


def test_push_force(foo_path, tsrc_cli):
    tsrc.git.run_git(foo_path, "checkout", "-b", "new-feature")
    tsrc.git.run_git(foo_path, "commit", "--message", "one", "--allow-empty")
    tsrc.git.run_git(foo_path, "commit", "--message", "two", "--allow-empty")
    tsrc.git.run_git(foo_path, "push", "origin", "new-feature:new-feature")
    tsrc.git.run_git(foo_path, "reset", "--hard", "HEAD~1")
    with mock.patch("tsrc.gitlab") as mock_gitlab:
        tsrc_cli.run("push", "--force")


def test_select_user():
    users = [TIMOTHEE, THEO]
    assert tsrc.cli.push.get_assignee(users, 'tim') == TIMOTHEE
    assert tsrc.cli.push.get_assignee(users, 'theo') == THEO
    with pytest.raises(tsrc.Error) as e:
        tsrc.cli.push.get_assignee(users, 't')
    print(e.value.message)
    assert "several" in e.value.message
    users = [JOHN, BART]
    with pytest.raises(tsrc.Error) as e:
        tsrc.cli.push.get_assignee(users, 'jhon')
    print(e.value.message)
    assert "Did you mean" in e.value.message
