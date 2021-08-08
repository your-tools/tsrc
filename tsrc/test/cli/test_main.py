import pytest

from tsrc.cli.main import main


def test_without_args() -> None:
    with pytest.raises(SystemExit) as e:
        main([])
    assert e.value.code != 0


def test_help() -> None:
    with pytest.raises(SystemExit) as e:
        main(["-h"])
    assert e.value.code == 0


def test_version() -> None:
    with pytest.raises(SystemExit) as e:
        main(["--version"])
    assert e.value.code == 0
