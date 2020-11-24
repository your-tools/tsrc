from cli_ui.tests import MessageRecorder

from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer


def test_happy(
    tsrc_cli: CLI, git_server: GitServer, message_recorder: MessageRecorder
) -> None:
    """
    Scenario:
    * Create a manifest with two repos, foo and bar
    * Initialize a workspace from this manifest
    * Create a tag named v0.1 on foo and bar
    * Run `tsrc log --from v0.1
    """
    git_server.add_repo("foo")
    git_server.add_repo("spam")
    git_server.push_file("foo", "bar.txt", message="boring bar")
    git_server.tag("foo", "v0.1")
    git_server.tag("spam", "v0.1")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)
    git_server.push_file("foo", "foo.txt", message="new foo!")
    tsrc_cli.run("sync")
    message_recorder.reset()

    tsrc_cli.run("log", "--from", "v0.1")

    assert message_recorder.find("new foo!")

    message_recorder.reset()
    tsrc_cli.run("log", "--from", "v0.1", "--to", "v0.1")
    assert not message_recorder.find("new foo!")


def test_log_error(tsrc_cli: CLI, git_server: GitServer) -> None:
    """
    Scenario:
    * Create a manifest with one repo, foo
    * Initialize a workspace from this manifest
    * Check that `tsrc log --from v0.1` fails (the `v0.1` tag does not exist)
    """
    git_server.add_repo("foo")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url)

    tsrc_cli.run_and_fail("log", "--from", "v0.1")


def test_use_given_group(tsrc_cli: CLI, git_server: GitServer) -> None:
    """
    Scenario:
    * Create a manifest containing:
      * a group named 'group1' containing the repo 'foo'
      * a group named 'group2' containing the repo 'bar'
    * Initialize a workspace from this manifest using the 'group1' and
    'group2' groups
    * Create a tag named v0.1 on foo
    * Run `tsrc --log --from v0.1 --group group1`
    """

    git_server.add_group("group1", ["foo"])
    git_server.add_group("group2", ["bar"])

    manifest_url = git_server.manifest_url
    git_server.tag("foo", "v0.1")
    git_server.push_file("foo", "foo.txt", message="new foo!")

    tsrc_cli.run("init", manifest_url, "--groups", "group1", "group2")
    tsrc_cli.run("log", "--from", "v0.1", "--group", "group1")


def test_missing_repos_from_given_group(
    tsrc_cli: CLI, git_server: GitServer, message_recorder: MessageRecorder
) -> None:
    """
    Scenario:
    * Create a manifest with two disjoint groups, group1 and group2
    * For each repo, create  v0.1 tag
    * Initialize a workspace from this manifest using group1
    * Run `tsrc log --from v0.1 --groups group1 group2`
    * Check it fails
    """
    git_server.add_group("group1", ["foo"])
    git_server.add_group("group2", ["bar"])
    git_server.tag("foo", "v0.1")
    git_server.tag("bar", "v0.1")
    manifest_url = git_server.manifest_url
    tsrc_cli.run("init", manifest_url, "--group", "group1")

    message_recorder.reset()
    tsrc_cli.run_and_fail("log", "--from", "v0.1", "--groups", "group1", "group2")
