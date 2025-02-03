""" Implementation of the tsrc Workspace: a collection of git repositories
"""

from pathlib import Path
from typing import List, Optional, Union

import cli_ui as ui
import ruamel.yaml

from tsrc.cleaner import Cleaner
from tsrc.cloner import Cloner
from tsrc.errors import Error
from tsrc.executor import process_items
from tsrc.file_system_operator import FileSystemOperator
from tsrc.git import is_git_repository
from tsrc.local_manifest import LocalManifest
from tsrc.manifest import Manifest
from tsrc.manifest_common_data import ManifestsTypeOfData
from tsrc.remote_setter import RemoteSetter
from tsrc.repo import Repo
from tsrc.syncer import Syncer
from tsrc.workspace_config import WorkspaceConfig


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
            manifest_branch_0=old_dict.get("branch"),
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

    def get_manifest_safe_mode(self, mtod: ManifestsTypeOfData) -> Manifest:
        return self.local_manifest.get_manifest_safe_mode(
            mtod,
        )

    def update_manifest(self) -> None:
        manifest_url = self.config.manifest_url
        manifest_branch = self.config.manifest_branch
        self.config.manifest_branch_0 = manifest_branch
        self.config.save_to_file(self.cfg_path)

        self.local_manifest.update(url=manifest_url, branch=manifest_branch)

    def _must_match_all_group_items(
        self, manifest: Manifest, groups: List[str], found_groups: List[str]
    ) -> bool:
        # go through all items in 'groups' as all items on each group has to
        # be found in 'found_groups' items
        need_items: List[str] = []  # all the items of all the 'groups'
        found_items: List[str] = []  # all that are found
        if manifest.group_list and manifest.group_list.groups:
            for name, group in manifest.group_list.groups.items():
                if name in groups:
                    need_items += group.elements
                if name in found_groups:
                    found_items += group.elements
        if set(need_items) == set(need_items).intersection(found_items):
            return True
        return False

    def update_config_on_switch(
        self,
        manifest: Manifest,
        found_groups: Optional[List[str]],
        groups: Optional[List[str]],
    ) -> Union[bool, None]:
        # we are switching, so Groups will be new in config
        ret_val: Union[bool, None] = None
        manifest = self.local_manifest.get_manifest()
        if manifest._switch and manifest._switch._groups:
            if found_groups and groups:
                matched_groups = list(
                    set(manifest._switch._groups).intersection(found_groups)
                )
                if matched_groups:
                    self.config.repo_groups = matched_groups
                    ret_val = True
                else:
                    # we may accept even Group, that does not match
                    # only if all items of such group
                    # can be found in 'groups' items
                    if (
                        self._must_match_all_group_items(
                            manifest, groups, manifest._switch._groups
                        )
                        is True
                    ):
                        self.config.repo_groups = groups
                        ret_val = True
                    else:
                        return None
            elif groups:
                return None
            else:
                self.config.repo_groups = list(manifest._switch._groups)
                ret_val = True
            if ret_val is True:
                ui.info_2("Using Manifest's switch configuration")
        else:
            if found_groups and groups:
                self.config.repo_groups = found_groups
                ret_val = True
            elif groups:
                return None
            else:
                self.config.repo_groups = []
                ret_val = True
                ui.info_2(
                    "No Manifest's switch configuration found, using default configuration"
                )
                ret_val = True
        self.config.save_to_file(self.cfg_path)
        return ret_val

    def update_config_repo_groups(
        self,
        groups: Optional[List[str]],
        ignore_group_item: bool = False,
        want_groups: Optional[List[str]] = None,
    ) -> None:
        if groups:
            self.config.repo_groups = groups
            self.config.save_to_file(self.cfg_path)
        else:
            if ignore_group_item is True:
                local_manifest = self.local_manifest.get_manifest_safe_mode(
                    ManifestsTypeOfData.LOCAL
                )
            else:
                local_manifest = self.local_manifest.get_manifest()
            if local_manifest.group_list:
                possible_groups = list(local_manifest.group_list.groups)
                if want_groups:
                    self.config.repo_groups = list(
                        set(want_groups).intersection(possible_groups)
                    )
                else:  # keep those that are possible & configured
                    self.config.repo_groups = list(
                        set(self.config.repo_groups).intersection(possible_groups)
                    )

                self.config.save_to_file(self.cfg_path)

    def clone_missing(self, *, num_jobs: int = 1) -> None:
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

    def set_remotes(self, num_jobs: int = 1) -> None:
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
        self,
        manifest: Optional[Manifest] = None,
        ignore_group_item: bool = False,
    ) -> None:
        repos = self.repos
        if not manifest:
            if ignore_group_item is True:
                manifest = self.get_manifest_safe_mode(ManifestsTypeOfData.LOCAL)
            else:
                manifest = self.get_manifest()
        operator = FileSystemOperator(self.root_path, repos)
        operations = manifest.file_system_operations
        known_repos = [x.dest for x in repos]
        operations = [x for x in operations if x.get_repo() in known_repos]
        if operations:
            ui.info_2("Performing filesystem operations")
            # Not sure it's a good idea to have FileSystemOperations running in parallel
            collection = process_items(operations, operator, num_jobs=1)
            collection.print_summary()
            if collection.errors:
                ui.error("Failed to perform the following file system operations")
                collection.print_errors()
                raise FileSystemOperatorError

    def sync(
        self,
        *,
        singular_remote: str = "",
        correct_branch: bool = False,
        force: bool = False,
        num_jobs: int = 1,
    ) -> None:
        remote_name = ""
        if singular_remote:
            remote_name = singular_remote
        elif self.config.singular_remote:
            remote_name = self.config.singular_remote
        syncer = Syncer(
            self.root_path,
            force=force,
            remote_name=remote_name,
            correct_branch=correct_branch,
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

    def clean(
        self, *, do_clean: bool = False, do_hard_clean: bool = False, num_jobs: int = 1
    ) -> None:
        """
        optional. only runs when some of the cleans are True
        WARNING: this may lead to data loss of files that are not under the
        version control
        """
        if do_clean is True and do_hard_clean is True:
            ui.warning(
                "'--hard-clean' also performs '--clean', no need for extra option"
            )

        clean_mode: int = 0
        if do_hard_clean is True:
            clean_mode = 2
        else:
            if do_clean is True:
                clean_mode = 1

        if clean_mode > 0:
            this_hard: bool = False
            if clean_mode == 2:
                this_hard = True

            cleaner = Cleaner(self.root_path, do_hard_clean=this_hard)
            repos = self.repos
            ui.info_2("Cleaning repos:")
            process_items(repos, cleaner, num_jobs=num_jobs)


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
