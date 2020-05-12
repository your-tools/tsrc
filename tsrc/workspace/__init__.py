""" Implementation of the tsrc Workspace: a collection of git repositories
"""

from typing import Iterable, List, Tuple

import cli_ui as ui
from path import Path
import ruamel.yaml

import tsrc
import tsrc.executor
import tsrc.git

from .cloner import Cloner
from .copier import FileCopier
from .syncer import Syncer
from .remote_setter import RemoteSetter
from .local_manifest import LocalManifest
from .config import WorkspaceConfig


def copy_cfg_path_if_needed(root_path: Path) -> None:
    """ Backward compatibility layer with tsrc < 1.0 """
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
        # Note: at the repositories on which the user wishes to
        # execute an action is unknown. It will be set
        # this list after processing the command line arguments
        # (like `--group` or `--all`)
        #
        # Note: you _cannot assume_ that every repo in this list was
        # cloned (in other words, don't use `workspace.root_path / repo.src`
        # without checking that the path exists)!
        # This is because there can be a mismatch between the state of
        # the workspace and the requested repos - for instance, the user could
        # have configured a workspace with a `backend` group, but using
        # a disjoint `front-end` group on the command line.
        self.repos: List[tsrc.Repo] = []

    def get_manifest(self) -> tsrc.Manifest:
        return self.local_manifest.get_manifest()

    def update_manifest(self) -> None:
        manifest_url = self.config.manifest_url
        manifest_branch = self.config.manifest_branch
        self.local_manifest.update(url=manifest_url, branch=manifest_branch)

    def clone_missing(self) -> None:
        to_clone = []
        for repo in self.repos:
            repo_path = self.root_path / repo.src
            if not repo_path.exists():
                to_clone.append(repo)
        cloner = Cloner(self.root_path, shallow=self.config.shallow_clones)
        tsrc.executor.run_sequence(to_clone, cloner)

    def set_remotes(self) -> None:
        remote_setter = RemoteSetter(self.root_path)
        tsrc.executor.run_sequence(self.repos, remote_setter)

    def copy_files(self) -> None:
        repos = self.repos
        file_copier = FileCopier(self.root_path, repos)
        manifest = self.local_manifest.get_manifest()
        copyfiles = manifest.copyfiles
        tsrc.executor.run_sequence(copyfiles, file_copier)

    def sync(self, *, force: bool = False) -> None:
        repos = self.repos
        syncer = Syncer(self.root_path, force=force)
        try:
            tsrc.executor.run_sequence(repos, syncer)
        finally:
            syncer.display_bad_branches()

    def enumerate_repos(self) -> Iterable[Tuple[int, tsrc.Repo, Path]]:
        """ Yield (index, repo, full_path) for all the repos """
        for i, repo in enumerate(self.repos):
            full_path = self.root_path / repo.src
            yield (i, repo, full_path)


class WorkspaceNotConfigured(tsrc.Error):
    def __init__(self, root_path: Path):
        message = "Workspace in {} is not configured. Please run `tsrc init`"
        super().__init__(message.format(root_path))
