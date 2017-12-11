import tsrc.cli


def assert_shallow_clone(workspace_path, repo):
    repo_path = workspace_path.joinpath(repo)
    assert tsrc.git.is_shallow(repo_path)


def test_shallow_clone_with_tag(tsrc_cli, git_server, workspace_path):
    git_server.add_repo("foo")
    git_server.tag("foo", "v1.0")
    git_server.manifest.set_repo_tag("foo", "v1.0")
    git_server.manifest.set_shallow_repo("foo")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init",  manifest_url)
    assert_shallow_clone(workspace_path, "foo")


def test_shallow_clone_with_branch(tsrc_cli, git_server, workspace_path):
    git_server.add_repo("foo")
    git_server.manifest.set_shallow_repo("foo")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init",  manifest_url)
    assert_shallow_clone(workspace_path, "foo")


def test_shallow_with_sha1(tsrc_cli, git_server, workspace_path, message_recorder):
    git_server.add_repo("foo")
    initial_sha1 = git_server.get_sha1("foo")
    git_server.push_file("foo", "one.c")
    git_server.manifest.set_repo_sha1("foo", initial_sha1)
    git_server.manifest.set_shallow_repo("foo")

    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url, expect_fail=True)
    assert message_recorder.find("shallow repository with a fixed sha1")
