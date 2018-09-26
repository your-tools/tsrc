import argparse
from typing import Any, List

from gitlab import Gitlab
from path import Path
import mock


import tsrc
from tsrc.test.helpers.cli import CLI
from tsrc.cli.push import RepositoryInfo
from tsrc.cli.push_gitlab import PushAction


GITLAB_URL = "http://gitlab.example.com"

ALICE = mock.Mock(username="alice", id=1)
BOB = mock.Mock(username="bob", id=2)
EVE = mock.Mock(username="eve", id=3)


class UserList:

    def __init__(self, user_list: List[Any]) -> None:
        self.user_list = user_list
        self.index = -1
        self.total = len(user_list)
        self.next_page = None

    def __iter__(self) -> Any:
        return (user for user in self.user_list)


def execute_query(*, query: str, **kwargs: Any) -> UserList:
    matches = list()
    for user in [ALICE, BOB, EVE]:
        if user.username == query:
            matches.append(user)
    return UserList(matches)


def gitlab_mock_with_merge_requests(mock_merge_requests: List[Any]) -> Any:
    gitlab_mock = mock.Mock()

    mock_project = mock.Mock()
    mock_project.members.list.side_effect = execute_query
    mock_project.mergerequests.list.return_value = mock_merge_requests

    mock_group = mock.Mock()
    mock_group.members.list.side_effect = execute_query

    gitlab_mock.projects.get.return_value = mock_project

    gitlab_mock.groups.get.return_value = mock_group

    return gitlab_mock


def execute_push(repo_path: Path, push_args: argparse.Namespace, gitlab_mock: Gitlab) -> None:
    repository_info = RepositoryInfo()
    repository_info.read_working_path(repo_path)
    push_action = PushAction(repository_info, push_args, gitlab_api=gitlab_mock)
    push_action.execute()


def test_creating_merge_request_explicit_target_branch_with_assignee(
        repo_path: Path, tsrc_cli: CLI,
        push_args: argparse.Namespace) -> None:
    tsrc.git.run(repo_path, "checkout", "-b", "new-feature")
    tsrc.git.run(repo_path, "commit", "--message", "new feature", "--allow-empty")

    gitlab_mock = gitlab_mock_with_merge_requests([])

    push_args.assignee = "alice"
    push_args.target_branch = "next"
    push_args.title = "Best feature ever"

    mock_project = gitlab_mock.projects.get()
    new_mr = mock.Mock()
    mock_project.mergerequests.create.return_value = new_mr
    execute_push(repo_path, push_args, gitlab_mock)

    mock_project.mergerequests.create.assert_called_once_with(
        {
            "source_branch": "new-feature",
            "target_branch": "next",
            "title": "new-feature",
        }
    )

    new_mr.title = "Best feature ever"
    new_mr.save.assert_called_once_with()


def test_creating_merge_request_uses_default_branch(
        repo_path: Path, tsrc_cli: CLI, push_args: argparse.Namespace) -> None:

    gitlab_mock = gitlab_mock_with_merge_requests([])
    mock_project = gitlab_mock.projects.get()
    mock_project.default_branch = "devel"
    tsrc.git.run(repo_path, "checkout", "-b", "new-feature")
    tsrc.git.run(repo_path, "commit", "--message", "new feature", "--allow-empty")

    mock_project = gitlab_mock.projects.get()
    new_mr = mock.Mock(iid="43", web_url="http://43")
    mock_project.mergerequests.create.return_value = new_mr

    push_args.assignee = "alice"
    execute_push(repo_path, push_args, gitlab_mock)

    mock_project.mergerequests.create.assert_called_once_with(
        {
            "source_branch": "new-feature",
            "target_branch": "devel",
            "title": "new-feature",
        }
    )


def test_set_approvers(repo_path: Path, tsrc_cli: CLI, push_args: argparse.Namespace) -> None:

    tsrc.git.run(repo_path, "checkout", "-b", "new-feature")
    tsrc.git.run(repo_path, "commit", "--message", "new feature", "--allow-empty")

    push_args.reviewers = ["alice", "eve"]

    mock_mr = mock.Mock(iid="42", web_url="http://42")
    gitlab_mock = gitlab_mock_with_merge_requests([mock_mr])

    execute_push(repo_path, push_args, gitlab_mock)

    mock_mr.approvals.set_approvers.assert_called_once_with([ALICE.id, EVE.id])
    mock_mr.save.assert_called_once()


def test_update_existing_merge_request(repo_path: Path, tsrc_cli: CLI,
                                       push_args: argparse.Namespace) -> None:
    tsrc.git.run(repo_path, "checkout", "-b", "new-feature")
    tsrc.git.run(repo_path, "commit", "--message", "new feature", "--allow-empty")

    mock_mr = mock.Mock(iid="42", web_url="http://42", title="old title")
    gitlab_mock = gitlab_mock_with_merge_requests([mock_mr])

    push_args.target_branch = "next"
    push_args.title = "Best feature ever"
    execute_push(repo_path, push_args, gitlab_mock)

    gitlab_mock.mergerequests.create.assert_not_called()
    assert mock_mr.remove_source_branch
    assert mock_mr.target_branch == "next"
    assert mock_mr.title == "Best feature ever"


def test_close_merge_request(repo_path: Path, tsrc_cli: CLI,
                             push_args: argparse.Namespace) -> None:
    tsrc.git.run(repo_path, "checkout", "-b", "new-feature")
    tsrc.git.run(repo_path, "commit", "--message", "new feature", "--allow-empty")

    mock_mr = mock.Mock(iid="42", web_url="http://42", title="old title")
    gitlab_mock = gitlab_mock_with_merge_requests([mock_mr])

    push_args.close = True
    execute_push(repo_path, push_args, gitlab_mock)

    assert mock_mr.state_event == "close"
    mock_mr.save.assert_called_once()


def test_do_not_change_mr_target(repo_path: Path, tsrc_cli: CLI,
                                 push_args: argparse.Namespace) -> None:

    mock_mr = mock.Mock(iid="42", web_url="http://42", target_branch="old-branch")
    gitlab_mock = gitlab_mock_with_merge_requests([mock_mr])

    execute_push(repo_path, push_args, gitlab_mock)

    assert mock_mr.target_branch == "old-branch"


def test_accept_merge_request(repo_path: Path, tsrc_cli: CLI,
                              push_args: argparse.Namespace) -> None:
    tsrc.git.run(repo_path, "checkout", "-b", "new-feature")
    tsrc.git.run(repo_path, "commit", "--message", "new feature", "--allow-empty")

    mock_mr = mock.Mock(iid="42", web_url="http://42", target_branch="old-branch")
    gitlab_mock = gitlab_mock_with_merge_requests([mock_mr])

    push_args.accept = True
    execute_push(repo_path, push_args, gitlab_mock)

    mock_mr.merge.assert_called_once_with(merge_when_pipeline_succeeds=True)


def test_unwipify_existing_merge_request(repo_path: Path, tsrc_cli: CLI,
                                         push_args: argparse.Namespace) -> None:
    mock_mr = mock.Mock(
        title="WIP: nice title",
        web_url="http://example.com/42",
        iid=42,
    )
    gitlab_mock = gitlab_mock_with_merge_requests([mock_mr])

    push_args.ready = True
    execute_push(repo_path, push_args, gitlab_mock)

    assert mock_mr.title == "nice title"
    mock_mr.save.assert_called_once()


def test_wipify_existing_merge_request(repo_path: Path, tsrc_cli: CLI,
                                       push_args: argparse.Namespace) -> None:
    mock_mr = mock.Mock(
        title="not ready",
        web_url="http://example.com/42",
        iid=42,
    )
    gitlab_mock = gitlab_mock_with_merge_requests([mock_mr])

    push_args.wip = True
    execute_push(repo_path, push_args, gitlab_mock)

    assert mock_mr.title == "WIP: not ready"
    mock_mr.save.assert_called_once()
