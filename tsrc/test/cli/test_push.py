import argparse

from path import Path
import tsrc
from tsrc.cli.push import PushAction


class DummyPush(PushAction):
    def post_push(self) -> None:
        pass

    def setup_service(self) -> None:
        pass


def test_push_use_tracked_branch(repo_path: Path, push_args: argparse.Namespace) -> None:
    tsrc.git.run(repo_path, "checkout", "-b", "local")
    tsrc.git.run(repo_path, "push", "-u", "origin", "local:remote")
    repository_info = tsrc.cli.push.RepositoryInfo(repo_path)
    dummy_push = DummyPush(repository_info, push_args)
    dummy_push.push()
    _, out = tsrc.git.run_captured(repo_path, "ls-remote")
    assert "local" not in out
    assert "heads/remote" in out


def test_push_use_given_push_spec(repo_path: Path, push_args: argparse.Namespace) -> None:
    tsrc.git.run(repo_path, "checkout", "-b", "local")
    push_args.push_spec = "local:remote"
    repository_info = tsrc.cli.push.RepositoryInfo(repo_path)
    dummy_push = DummyPush(repository_info, push_args)
    dummy_push.push()
    _, out = tsrc.git.run_captured(repo_path, "ls-remote")
    assert "local" not in out
    assert "heads/remote" in out
