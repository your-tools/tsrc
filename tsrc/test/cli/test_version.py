from tsrc.test.helpers.cli import CLI
from cli_ui.tests import message_recorder  # noqa


def test_version(tsrc_cli: CLI, message_recorder: message_recorder) -> None:
    tsrc_cli.run("version")
    assert message_recorder.find("version")
