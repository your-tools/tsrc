""" Manifest support. """

# TODO: check for absolute paths in _handle_copies, _handle_links

from pathlib import Path
from typing import Any, List, Optional

import schema

from tsrc.config import parse_config
from tsrc.errors import (
    Error,
    InvalidConfigError,
    LoadManifestSchemaError,
    LoadManifestSwitchConfigGroupsError,
)
from tsrc.file_system import Copy, FileSystemOperation, Link
from tsrc.groups import GroupList
from tsrc.manifest_common_data import ManifestsTypeOfData, mtod_can_ignore_remotes
from tsrc.repo import Remote, Repo
from tsrc.switch import Switch


class RepoNotFound(Error):
    def __init__(self, dest: str) -> None:
        super().__init__(f"No repo found in '{dest}'")


class Manifest:
    """Contains a list of `Repo` instances, and optionally
    a group list.

    """

    def __init__(self) -> None:
        self._repos: List[Repo] = []
        self.group_list: Optional[GroupList[str]] = None
        self._switch: Optional[Switch] = None

    def apply_config(
        self,
        config: Any,
        ignore_on_mtod: Optional[ManifestsTypeOfData] = None,
    ) -> None:
        """Apply config coming form the yaml file"""
        # Note: we cannot just serialize the yaml file into the class,
        # because we need to convert the plain old dicts into
        # higher-level classes.
        self.file_system_operations: List[FileSystemOperation] = []
        self.symlinks: List[Link] = []
        repos_config = config["repos"]
        for repo_config in repos_config:
            self._handle_repo(repo_config)
            self._handle_copies(repo_config)
            self._handle_links(repo_config)

        groups_config = config.get("groups")
        self._handle_groups(
            groups_config,
            ignore_on_mtod=ignore_on_mtod,
        )

        switch_config = config.get("switch")
        self._handle_switch(switch_config)

    def _handle_repo(self, repo_config: Any) -> None:
        dest = repo_config["dest"]
        branch = orig_branch = repo_config.get("branch")
        tag = repo_config.get("tag")
        sha1 = repo_config.get("sha1")
        url = repo_config.get("url")
        ignore_submodules = repo_config.get("ignore_submodules", False)
        if url:
            origin = Remote(name="origin", url=url)
            remotes = [origin]
        else:
            remotes = self._handle_remotes(repo_config)
        repo = Repo(
            dest=dest,
            branch=branch,
            orig_branch=orig_branch,
            sha1=sha1,
            tag=tag,
            remotes=remotes,
            ignore_submodules=ignore_submodules,
        )
        self._repos.append(repo)

    def _handle_remotes(self, repo_config: Any) -> List[Remote]:
        remotes_config = repo_config.get("remotes")
        res = []
        if remotes_config:
            for remote_config in remotes_config:
                remote = Remote(name=remote_config["name"], url=remote_config["url"])
                res.append(remote)
        return res

    def _handle_copies(self, repo_config: Any) -> None:
        if "copy" not in repo_config:
            return
        to_cp = repo_config["copy"]
        for item in to_cp:
            src = item["file"]
            dest = item.get("dest", src)
            copy = Copy(repo_config["dest"], src, dest)
            self.file_system_operations.append(copy)

    def _handle_links(self, repo_config: Any) -> None:
        if "symlink" not in repo_config:
            return
        to_link = repo_config["symlink"]
        for item in to_link:
            source = item["source"]
            target = item["target"]
            link = Link(repo_config["dest"], source, target)
            self.file_system_operations.append(link)

    def _handle_groups(
        self, groups_config: Any, ignore_on_mtod: Optional[ManifestsTypeOfData] = None
    ) -> None:
        elements = [repo.dest for repo in self._repos]
        self.group_list = GroupList(elements=elements)
        if not groups_config:
            return
        for name, group_config in groups_config.items():
            elements = group_config["repos"]
            includes = group_config.get("includes", [])
            self.group_list.add(
                name,
                elements,
                includes=includes,
                ignore_on_mtod=ignore_on_mtod,
            )

    def _handle_switch(self, switch_config: Any) -> None:
        self._switch = Switch(switch_config)

        # verify if groups in switch>config>groups are present in 'groups'
        if self.group_list and self.group_list.groups and self._switch._groups:
            switch_groups = list(self._switch._groups)
            groups_groups = self.group_list.groups.keys()
            if switch_groups and groups_groups:
                if set(switch_groups) != set(groups_groups).intersection(switch_groups):
                    raise LoadManifestSwitchConfigGroupsError()
        elif self._switch._groups:
            # you cannot have 'swtich>config>groups' alone (without 'groups')
            raise LoadManifestSwitchConfigGroupsError()

    def get_repos(
        self,
        groups: Optional[List[str]] = None,
        do_switch: bool = False,
        all_: bool = False,
        ignore_if_group_not_found: bool = False,
    ) -> List[Repo]:
        if all_:
            return self._repos

        if do_switch is True:
            return self._get_repos_on_switch(groups)

        if not groups:
            if self._has_default_group():
                return self._get_repos_in_groups(["default"])
            else:
                return self._repos

        return self._get_repos_in_groups(groups, ignore_if_group_not_found)

    def _has_default_group(self) -> bool:
        assert self.group_list
        return self.group_list.get_group("default") is not None

    def _get_repos_on_switch(self, groups: Optional[List[str]]) -> List[Repo]:
        if self._switch:
            if self._switch._groups:
                matched_groups = list(self._switch._groups)
                return self._get_repos_in_groups(matched_groups)
        return self._repos  # all repos

    def _get_repos_in_groups(
        self,
        groups: List[str],
        ignore_if_group_not_found: bool = False,
    ) -> List[Repo]:
        assert self.group_list
        elements = self.group_list.get_elements(
            groups=groups, ignore_if_group_not_found=ignore_if_group_not_found
        )
        res = []
        for dest in elements:
            res.append(self.get_repo(dest))
        return res

    def get_repo(self, dest: str) -> Repo:
        for repo in self._repos:
            if repo.dest == dest:
                return repo
        raise RepoNotFound(dest)


def validate_repo(data: Any) -> None:
    copy_schema = {"file": str, schema.Optional("dest"): str}
    symlink_schema = {"source": str, "target": str}
    remote_schema = {"name": str, "url": str}
    repo_schema = schema.Schema(
        {
            "dest": str,
            schema.Optional("branch"): str,
            schema.Optional("copy"): [copy_schema],
            schema.Optional("symlink"): [symlink_schema],
            schema.Optional("sha1"): str,
            schema.Optional("tag"): str,
            schema.Optional("ignore_submodules"): bool,
            schema.Optional("remotes"): [remote_schema],
            schema.Optional("url"): str,
        }
    )
    repo_schema.validate(data)
    url = data.get("url")
    remotes = data.get("remotes")
    if url and remotes:
        raise schema.SchemaError(
            "Repo config cannot contain both an url and a list of remotes"
        )
    if not url and not remotes:
        raise schema.SchemaError(
            "Repo config should contain either a url or a non-empty list of remotes"
        )


def validate_repo_no_remote_required(data: Any) -> None:
    copy_schema = {"file": str, schema.Optional("dest"): str}
    symlink_schema = {"source": str, "target": str}
    remote_schema = {"name": str, "url": str}
    repo_schema = schema.Schema(
        {
            "dest": str,
            schema.Optional("branch"): str,
            schema.Optional("copy"): [copy_schema],
            schema.Optional("symlink"): [symlink_schema],
            schema.Optional("sha1"): str,
            schema.Optional("tag"): str,
            schema.Optional("ignore_submodules"): bool,
            schema.Optional("remotes"): [remote_schema],
            schema.Optional("url"): str,
        }
    )
    repo_schema.validate(data)
    url = data.get("url")
    remotes = data.get("remotes")
    if url and remotes:
        raise schema.SchemaError(
            "Repo config cannot contain both an url and a list of remotes"
        )


def validate_switch_config(data: Any) -> None:
    switch_config_schema = schema.Schema(
        {
            schema.Optional("groups"): [str],
        }
    )
    switch_config_schema.validate(data)


def validate_switch(data: Any) -> None:
    on_config_schema = schema.Use(validate_switch_config)
    switch_schema = schema.Schema({schema.Optional("config"): on_config_schema})
    switch_schema.validate(data)


def load_manifest(manifest_path: Path) -> Manifest:
    """Main entry point: return a manifest instance by parsing
    a `manifest.yml` file.

    """
    remote_git_server_schema = {"url": str}
    repo_schema = schema.Use(validate_repo)
    group_schema = {"repos": [str], schema.Optional("includes"): [str]}
    # Note: gitlab and github_enterprise_url keys are ignored,
    # and kept here only for backward compatibility reasons
    on_switch_schema = schema.Use(validate_switch)
    manifest_schema = schema.Schema(
        {
            "repos": [repo_schema],
            schema.Optional("gitlab"): remote_git_server_schema,
            schema.Optional("github_enterprise"): remote_git_server_schema,
            schema.Optional("groups"): {str: group_schema},
            schema.Optional("switch"): on_switch_schema,
        }
    )
    parsed = parse_config(manifest_path, schema=manifest_schema)
    res = Manifest()
    res.apply_config(parsed)
    return res


def load_manifest_safe_mode(manifest_path: Path, mtod: ManifestsTypeOfData) -> Manifest:
    """Main entry point: return a manifest instance by parsing
    a `manifest.yml` file.

    if we have demaged Repo (like 'url' is missing), just ignore Manifest.
    This is particulary useful when loading Manifest is not that important.

    if we have Group that contain Repo that is not present in the Manifest,
    ignore such Repo (do not add it to Group).
    """
    remote_git_server_schema = {"url": str}
    if mtod in mtod_can_ignore_remotes():
        repo_schema = schema.Use(validate_repo_no_remote_required)
    else:
        repo_schema = schema.Use(validate_repo)
    group_schema = {"repos": [str], schema.Optional("includes"): [str]}
    # Note: gitlab and github_enterprise_url keys are ignored,
    # and kept here only for backward compatibility reasons
    on_switch_schema = schema.Use(validate_switch)
    manifest_schema = schema.Schema(
        {
            "repos": [repo_schema],
            schema.Optional("gitlab"): remote_git_server_schema,
            schema.Optional("github_enterprise"): remote_git_server_schema,
            schema.Optional("groups"): {str: group_schema},
            schema.Optional("switch"): on_switch_schema,
        }
    )
    try:
        parsed = parse_config(manifest_path, schema=manifest_schema)
    except InvalidConfigError:
        raise LoadManifestSchemaError(mtod)

    parsed = parse_config(manifest_path, schema=manifest_schema)
    res = Manifest()
    res.apply_config(parsed, ignore_on_mtod=mtod)
    return res
