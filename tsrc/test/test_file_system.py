import os
from pathlib import Path

import pytest

import tsrc.file_system


def test_can_create_symlink_when_source_does_not_exist(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    target.touch()
    tsrc.file_system.safe_link(source=source, target=target)
    assert source.exists()
    assert source.resolve() == target.resolve()


def test_can_create_symlink_pointing_to_directory(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    target.mkdir(parents=True)
    tsrc.file_system.safe_link(source=source, target=target)

    assert source.exists()
    assert source.resolve() == target.resolve()


def test_cannot_create_symlink_when_source_is_a_file(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.touch()
    with pytest.raises(tsrc.Error) as e:
        tsrc.file_system.safe_link(source=source, target=target)
    assert "is not a link" in e.value.message


def test_can_update_broken_symlink(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    os.symlink(target, source)

    new_target = tmp_path / "new_target"
    new_target.touch()
    tsrc.file_system.safe_link(source=source, target=new_target)

    assert source.exists()
    assert source.resolve() == new_target.resolve()


def test_can_update_existing_symlink(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    target.touch()
    os.symlink(target, source)

    new_target = tmp_path / "new_target"
    tsrc.file_system.safe_link(source=source, target=new_target)

    new_target.touch()
    assert source.exists()
    assert source.resolve() == new_target.resolve()


def test_do_nothing_if_symlink_has_the_correct_target(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    target.touch()
    os.symlink(target, source)

    tsrc.file_system.safe_link(source=source, target=target)

    assert source.exists()
    assert source.resolve() == target.resolve()
