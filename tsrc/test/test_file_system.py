import os
from pathlib import Path

import pytest

from tsrc.errors import Error
from tsrc.file_system import safe_link


def test_can_create_symlink_when_source_does_not_exist(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    target.touch()
    safe_link(source=source, target=target)
    assert source.exists()
    assert source.resolve() == target.resolve()


def test_can_create_symlink_pointing_to_directory(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    target.mkdir(parents=True)
    safe_link(source=source, target=target)

    assert source.exists()
    assert source.resolve() == target.resolve()


def test_cannot_create_symlink_when_source_is_a_file(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.touch()
    with pytest.raises(Error) as e:
        safe_link(source=source, target=target)
    assert "is not a link" in e.value.message


def test_can_update_broken_symlink(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    os.symlink(target, source)

    new_target = tmp_path / "new_target"
    new_target.touch()
    safe_link(source=source, target=new_target)

    assert source.exists()
    assert source.resolve() == new_target.resolve()


def test_can_update_existing_symlink(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    target.touch()
    os.symlink(target, source)

    new_target = tmp_path / "new_target"
    safe_link(source=source, target=new_target)

    new_target.touch()
    assert source.exists()
    assert source.resolve() == new_target.resolve()


def test_do_nothing_if_symlink_has_the_correct_target(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    target.touch()
    os.symlink(target, source)

    safe_link(source=source, target=target)

    assert source.exists()
    assert source.resolve() == target.resolve()
