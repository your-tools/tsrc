import abc
import os
import shutil
from pathlib import Path

import attr
import cli_ui as ui

from tsrc.errors import Error


class FileSystemOperation(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def perform(self, workspace_path: Path) -> None:
        pass

    @abc.abstractmethod
    def __str__(self) -> str:
        pass


@attr.s(frozen=True)
class Copy(FileSystemOperation):
    repo: str = attr.ib()
    src: str = attr.ib()
    dest: str = attr.ib()

    def perform(self, workspace_path: Path) -> None:
        src_path = workspace_path / self.repo / self.src
        dest_path = workspace_path / self.dest
        shutil.copy(src_path, dest_path)

    def __str__(self) -> str:
        return f"copy from '{self.repo}/{self.src}' to '{self.dest}'"


@attr.s(frozen=True)
class Link(FileSystemOperation):
    repo: str = attr.ib()
    source: str = attr.ib()
    target: str = attr.ib()

    def perform(self, workspace_path: Path) -> None:
        source = workspace_path / self.source
        target = Path(self.target)
        safe_link(source=source, target=target)

    def __str__(self) -> str:
        return f"link from '{self.source}' to '{self.target}'"


def safe_link(*, source: Path, target: Path) -> None:
    """Safely create a link in 'source' pointing to 'target'."""
    # Not: we need to call both islink() and exist() to safely ensure
    # that the link exists:
    #
    #    islink()  exists()    Description
    #    ----------------------------------------------------------
    #    False     False       source does not currently exist : OK
    #    False     True        source corresponds to a file or dir : Error!
    #    True      False       broken symlink, need to remove
    #    True      True        symlink points to a valid target, check target
    #    ----------------------------------------------------------
    make_link = check_link(source=source, target=target)
    if make_link:
        ui.info_3("Creating link", source, "->", target)

        os.symlink(
            os.path.normpath(target),
            os.path.normcase(source),
            target_is_directory=target.is_dir(),
        )


def check_link(*, source: Path, target: Path) -> bool:
    remove_link = False
    if source.exists() and not source.is_symlink():
        raise Error("Specified symlink source exists but is not a link")
        return False
    if source.is_symlink():
        if source.exists():
            # symlink exists and points to some target
            current_target = Path(os.readlink(str(source)))
            if current_target.resolve() == target.resolve():
                ui.info_3("Leaving existing link")
                return False
            else:
                ui.info_3("Replacing existing link")
                remove_link = True
        else:
            # symlink exists, but points to a non-existent target
            ui.info_3("Replacing broken link")
            remove_link = True
    if remove_link:
        os.unlink(source)
    return True
