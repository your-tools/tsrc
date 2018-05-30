from tsrc.test.helpers.cli import CLI
from ui.tests.conftest import message_recorder


def test_version(tsrc_cli: CLI, message_recorder: message_recorder) -> None:
    tsrc_cli.run("version")
    assert message_recorder.find("version")
