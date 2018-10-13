from tsrc.test.helpers.cli import CLI


def test_help(tsrc_cli: CLI) -> None:
    tsrc_cli.run("--help")


def test_bad_args(tsrc_cli: CLI) -> None:
    tsrc_cli.run("bad", expect_fail=True)
