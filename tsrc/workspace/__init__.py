""" Implementation of the tsrc Workspace: a collection of git repositories
"""

from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import cli_ui as ui
import ruamel.yaml

from tsrc.errors import Error
from tsrc.executor import process_items
from tsrc.git import is_git_repository
from tsrc.manifest import Manifest
from tsrc.repo import Repo
from tsrc.workspace.cloner import Cloner
from tsrc.workspace.config import WorkspaceConfig
from tsrc.workspace.file_system_operator import FileSystemOperator
from tsrc.workspace.local_manifest import LocalManifest
from tsrc.workspace.remote_setter import RemoteSetter
from tsrc.workspace.syncer import Syncer


def copy_cfg_path_if_needed(root_path: Path) -> None:
    """Backward compatibility layer with tsrc < 1.0"""
    old_path = root_path / ".tsrc/manifest.yml"
    new_path = root_path / ".tsrc/config.yml"
    if old_path.exists() and not new_path.exists():
        ui.info("Migrating config to new path:", new_path)
        yaml = ruamel.yaml.YAML(typ="rt")
        old_dict = yaml.load(old_path.read_text())
        new_config = WorkspaceConfig(
            manifest_branch=old_dict.get("branch"),
            manifest_url=old_dict["url"],
            repo_groups=old_dict.get("groups"),
            shallow_clones=old_dict.get("shallow"),
        )
        new_config.save_to_file(new_path)


class Workspace:
    def __init__(self, root_path: Path) -> None:
        local_manifest_path = root_path / ".tsrc" / "manifest"
        self.cfg_path = root_path / ".tsrc" / "config.yml"
        self.root_path = root_path
        self.local_manifest = LocalManifest(local_manifest_path)
        copy_cfg_path_if_needed(root_path)
        if not self.cfg_path.exists():
            raise WorkspaceNotConfigured(root_path)

        self.config = WorkspaceConfig.from_file(self.cfg_path)

        # Note: at this point the repositories on which the user wishes to
        # execute an action is unknown. This list will be set after processing
        # the command line arguments (like `--group` or `--all-cloned`).
        #
        # In particular, you _cannot assume_ that every repo in this list was
        # cloned - in other words, don't use `workspace.root_path / repo.dest`
        # without checking that the path exists!
        # This is because there can be a mismatch between the state of
        # the workspace and the requested repos - for instance, the user could
        # have configured a workspace with a `backend` group, but using
        # a disjoint `front-end` group on the command line.
        self.repos: List[Repo] = []

    def get_manifest(self) -> Manifest:
        return self.local_manifest.get_manifest()

    def update_manifest(self) -> None:
        manifest_url = self.config.manifest_url
        manifest_branch = self.config.manifest_branch
        self.local_manifest.update(url=manifest_url, branch=manifest_branch)

    def clone_missing(self, *, num_jobs: Optional[int] = None) -> None:
        to_clone = []
        for repo in self.repos:
            repo_path = self.root_path / repo.dest
            if not is_git_repository(repo_path):
                to_clone.append(repo)
        cloner = Cloner(
            self.root_path,
            shallow=self.config.shallow_clones,
            remote_name=self.config.singular_remote,
        )
        ui.info_2("Cloning missing repos")
        collection = process_items(to_clone, cloner, num_jobs=num_jobs)
        if collection.summary:
            ui.info_2("Cloned repos:")
            for summary in collection.summary:
                ui.info(ui.green, "*", ui.reset, summary)
        if collection.errors:
            ui.error("Failed to clone the following repos")
            collection.print_errors()
            raise ClonerError

    def set_remotes(self, num_jobs: Optional[int] = None) -> None:
        if self.config.singular_remote:
            return
        ui.info_2("Configuring remotes")
        remote_setter = RemoteSetter(self.root_path)
        collection = process_items(self.repos, remote_setter, num_jobs=num_jobs)
        collection.print_summary()
        if collection.errors:
            ui.error("Failed to set remotes for the following repos:")
            collection.print_errors()
            raise RemoteSetterError

    def perform_filesystem_operations(
        self, manifest: Optional[Manifest] = None
    ) -> None:
        repos = self.repos
        if not manifest:
            manifest = self.get_manifest()
        operator = FileSystemOperator(self.root_path, repos)
        operations = manifest.file_system_operations
        known_repos = [x.dest for x in repos]
        operations = [x for x in operations if x.repo in known_repos]  # type: ignore
        if operations:
            ui.info_2("Performing filesystem operations")
            # Not sure it's a good idea to have FileSystemOperations running in parallel
            collection = process_items(operations, operator, num_jobs=None)
            collection.print_summary()
            if collection.errors:
                ui.error("Failed to perform the following file system operations")
                collection.print_errors()
                raise FileSystemOperatorError

    def sync(self, *, force: bool = False, num_jobs: Optional[int] = None) -> None:
        syncer = Syncer(
            self.root_path, force=force, remote_name=self.config.singular_remote
        )
        repos = self.repos
        ui.info_2("Synchronizing repos")
        collection = process_items(repos, syncer, num_jobs=num_jobs)
        if collection.summary:
            ui.info_2("Updated repos:")
            for summary in collection.summary:
                if summary:
                    ui.info(summary)
        if collection.errors:
            ui.error("Failed to synchronize the following repos:")
            collection.print_errors()
            raise SyncError

    def enumerate_repos(self) -> Iterable[Tuple[int, Repo, Path]]:
        """Yield (index, repo, full_path) for all the repos"""
        for i, repo in enumerate(self.repos):
            full_path = self.root_path / repo.dest
            yield (i, repo, full_path)


class SyncError(Error):
    pass


class ClonerError(Error):
    pass


class FileSystemOperatorError(Error):
    pass


class RemoteSetterError(Error):
    pass


class WorkspaceNotConfigured(Error):
    def __init__(self, root_path: Path):
        super().__init__(
            f"Workspace in '{root_path}' is not configured. Please run `tsrc init`"
        )
