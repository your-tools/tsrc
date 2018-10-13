from typing import Any, Dict, List, Tuple
import pytest

from path import Path
from .remote_manifest import RemoteManifest
from .bare_repo import BareRepo

RepoConfig = Dict[str, Any]
CopyConfig = Tuple[str, str]
RemoteConfig = Tuple[str, str]


class GitServer():
    def __init__(self, tmpdir: Path) -> None:
        self.tmpdir = tmpdir
        self.bare_path = tmpdir / "srv"
        self.src_path = tmpdir / "src"
        self.manifest = RemoteManifest.create(self.bare_path / "manifest")
        self.manifest_url = self.manifest.url

    def get_path(self, name: str) -> Path:
        return self.src_path / name

    def get_url(self, name: str) -> str:
        return str("file://" + (self.bare_path / name))

    def _get_bare_repo(self, name: str) -> BareRepo:
        bare_path = self.bare_path / name
        return BareRepo(bare_path)

    def _create_repo(self, name: str, empty: bool = False, branch: str = "master") -> str:
        bare_path = self.bare_path / name
        bare_repo = BareRepo.create(bare_path, branch=branch, empty=empty)
        return bare_repo.url

    def add_repo(self, name: str,
                 add_to_manifest: bool = True, empty: bool = False,
                 default_branch: str = "master") -> str:
        self._create_repo(name, empty=empty, branch=default_branch)
        url = self.get_url(name)
        if add_to_manifest:
            self.manifest.add_repo(name, url, branch=default_branch)
        return url

    def add_group(self, group_name: str, repos: List[str]) -> None:
        for repo in repos:
            self.add_repo(repo)
        self.manifest.configure_group(group_name, repos)

    def push_file(self, name: str, file_path: str, *,
                  contents: str = "", message: str = "", branch: str = "master") -> None:
        bare_repo = self._get_bare_repo(name)
        bare_repo.ensure_file(file_path, contents=contents, commit_message=message, branch=branch)

    def tag(self, name: str, tag_name: str) -> None:
        bare_repo = self._get_bare_repo(name)
        bare_repo.tag(tag_name)

    def get_tags(self, name: str) -> List[str]:
        bare_repo = self._get_bare_repo(name)
        return bare_repo.tags()

    def get_branches(self, name: str) -> List[str]:
        bare_repo = self._get_bare_repo(name)
        return bare_repo.branches()

    def get_sha1(self, name: str, branch: str) -> str:
        bare_repo = self._get_bare_repo(name)
        return bare_repo.get_sha1(branch)

    def delete_branch(self, name: str, branch: str) -> None:
        bare_repo = self._get_bare_repo(name)
        bare_repo.delete_branch(name)


@pytest.fixture
def git_server(tmp_path: Path) -> GitServer:
    return GitServer(tmp_path)
