import tsrc.cli.push


class DummyPush(tsrc.cli.push.PushAction):
    def post_push(self):
        pass

    def setup_service(self):
        pass


def test_push_use_tracked_branch(repo_path, push_args):
    tsrc.git.run_git(repo_path, "checkout", "-b", "local")
    tsrc.git.run_git(repo_path, "push", "-u", "origin", "local:remote")
    repository_info = tsrc.cli.push.RepositoryInfo(repo_path)
    dummy_push = DummyPush(repository_info, push_args)
    dummy_push.push()
    _, out = tsrc.git.run_git_captured(repo_path, "ls-remote")
    assert "local" not in out
    assert "heads/remote" in out


def test_push_use_given_push_spec(repo_path, push_args):
    tsrc.git.run_git(repo_path, "checkout", "-b", "local")
    push_args.push_spec = "local:remote"
    repository_info = tsrc.cli.push.RepositoryInfo(repo_path)
    dummy_push = DummyPush(repository_info, push_args)
    dummy_push.push()
    _, out = tsrc.git.run_git_captured(repo_path, "ls-remote")
    assert "local" not in out
    assert "heads/remote" in out
