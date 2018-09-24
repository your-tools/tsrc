""" Implementation of the tsrc Workspace: a collection of git repositories
"""

from typing import Iterable, List, Tuple

from path import Path

import tsrc
import tsrc.executor
import tsrc.git
import tsrc.manifest

from .manifest_config import ManifestConfig
from .cloner import Cloner
from .copier import FileCopier
from .syncer import Syncer
from .remote_setter import RemoteSetter
from .local_manifest import LocalManifest


class Workspace():
    def __init__(self, root_path: Path) -> None:
        self.root_path = root_path
        self.local_manifest = LocalManifest(root_path)

    def get_repos(self) -> List[tsrc.Repo]:
        return self.local_manifest.get_repos()

    def load_manifest(self) -> None:
        self.local_manifest.load()

    def get_gitlab_url(self) -> str:
        return self.local_manifest.get_gitlab_url()

    def configure_manifest(self, manifest_config: ManifestConfig) -> None:
        self.local_manifest.configure(manifest_config)

    def update_manifest(self) -> None:
        self.local_manifest.update()

    @property
    def active_groups(self) -> List[str]:
        return self.local_manifest.active_groups

    @property
    def shallow(self) -> bool:
        return self.local_manifest.shallow

    def clone_missing(self) -> None:
        to_clone = list()
        for repo in self.get_repos():
            repo_path = self.root_path / repo.src
            if not repo_path.exists():
                to_clone.append(repo)
        cloner = Cloner(self.root_path, shallow=self.shallow)
        tsrc.executor.run_sequence(to_clone, cloner)

    def set_remotes(self) -> None:
        remote_setter = RemoteSetter(self.root_path)
        tsrc.executor.run_sequence(self.get_repos(), remote_setter)

    def copy_files(self) -> None:
        file_copier = FileCopier(self.root_path)
        tsrc.executor.run_sequence(self.local_manifest.copyfiles, file_copier)

    def sync(self) -> None:
        syncer = Syncer(self.root_path)
        try:
            tsrc.executor.run_sequence(self.get_repos(), syncer)
        finally:
            syncer.display_bad_branches()

    def enumerate_repos(self) -> Iterable[Tuple[int, tsrc.Repo, Path]]:
        """ Yield (index, repo, full_path) for all the repos """
        for i, repo in enumerate(self.get_repos()):
            full_path = self.root_path / repo.src
            yield (i, repo, full_path)
