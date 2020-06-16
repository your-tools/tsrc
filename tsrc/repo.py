""" Repo objects """
from typing import Optional, List  # noqa

import abc

import attr
from path import Path

import tsrc.file_system


@attr.s(frozen=True)
class Remote:
    name = attr.ib()  # type: str
    url = attr.ib()  # type: str


class FileSystemOperation(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def perform(self, workspace_path: Path) -> None:
        pass

    @abc.abstractmethod
    def __str__(self) -> str:
        pass


@attr.s(frozen=True)
class Copy(FileSystemOperation):
    repo = attr.ib()  # type: str
    src = attr.ib()  # type: str
    dest = attr.ib()  # type: str

    def perform(self, workspace_path: Path) -> None:
        src_path = workspace_path / self.repo / self.src
        dest_path = workspace_path / self.dest
        src_path.copy(dest_path)

    def __str__(self) -> str:
        return f"copy from '{self.repo}/{self.src}' to '{self.dest}'"


@attr.s(frozen=True)
class Link(FileSystemOperation):
    repo = attr.ib()  # type: str
    source = attr.ib()  # type: str
    target = attr.ib()  # type: str

    def perform(self, workspace_path: Path) -> None:
        source = workspace_path / self.source
        target = Path(self.target)
        tsrc.file_system.safe_link(source=source, target=target)

    def __str__(self) -> str:
        return f"link from '{self.source}' to '{self.target}'"


@attr.s(frozen=True)
class Repo:
    dest = attr.ib()  # type: str
    remotes = attr.ib()  # type: List[Remote]
    branch = attr.ib(default="master")  # type: str
    sha1 = attr.ib(default=None)  # type: Optional[str]
    tag = attr.ib(default=None)  # type: Optional[str]
    shallow = attr.ib(default=False)  # type: bool

    @property
    def clone_url(self) -> str:
        assert self.remotes
        return self.remotes[0].url
