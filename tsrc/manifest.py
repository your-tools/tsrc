""" manifests for tsrc """

import operator
import os
from typing import cast, Any, Dict, List, NewType, Optional, Tuple # noqa

from path import Path
import schema

import tsrc
import tsrc.config
from tsrc.repo import Repo  # noqa
import tsrc.groups
from tsrc.groups import GroupList  # noqa

ManifestConfig = NewType('ManifestConfig', Dict[str, Any])
RepoConfig = NewType('RepoConfig', Dict[str, Any])

GitLabConfig = NewType('GitLabConfig', Dict[str, Any])


class RepoNotFound(tsrc.Error):
    def __init__(self, src: str) -> None:
        super().__init__("No repo found in '%s'" % src)


class Manifest():
    def __init__(self) -> None:
        self._repos = list()  # type: List[Repo]
        self.copyfiles = list()  # type: List[Tuple[str, str]]
        self.gitlab = None  # type: Optional[GitLabConfig]
        self.group_list = None  # type:  Optional[GroupList[str]]

    def load(self, config: ManifestConfig) -> None:
        self.copyfiles = list()
        self.gitlab = config.get("gitlab")
        repos = config.get("repos") or list()
        for repo_config in repos:
            url = repo_config["url"]
            src = repo_config["src"]
            branch = repo_config.get("branch", "master")
            tag = repo_config.get("tag")
            sha1 = repo_config.get("sha1")
            repo = tsrc.Repo(url=url, src=src, branch=branch,
                             sha1=sha1, tag=tag)
            self._repos.append(repo)

            self._handle_copies(repo_config)

        self._handle_groups(config)

    def _handle_copies(self, repo_config: RepoConfig) -> None:
        if "copy" not in repo_config:
            return
        to_cp = repo_config["copy"]
        for item in to_cp:
            src_copy = item["src"]
            dest_copy = item.get("dest", src_copy)
            src_copy = os.path.join(repo_config["src"], src_copy)
            self.copyfiles.append((src_copy, dest_copy))

    def _handle_groups(self, config: ManifestConfig) -> None:
        elements = set(repo.src for repo in self._repos)
        self.group_list = tsrc.groups.GroupList(elements=elements)
        groups_config = config.get("groups", dict())
        for name, group_config in groups_config.items():
            elements = group_config["repos"]
            includes = group_config.get("includes", list())
            self.group_list.add(name, elements, includes=includes)

    def get_repos(self, groups: Optional[List[str]] = None, all_: bool = False) -> List[tsrc.Repo]:
        if all_:
            return self._repos

        if not groups:
            if self._has_default_group():
                return self._get_repos_in_groups(["default"])
            else:
                return self._repos

        return self._get_repos_in_groups(groups)

    def _has_default_group(self) -> bool:
        assert self.group_list
        return self.group_list.get_group("default") is not None

    def _get_repos_in_groups(self, groups: List[str]) -> List[tsrc.Repo]:
        assert self.group_list
        elements = self.group_list.get_elements(groups=groups)
        res = list()
        for src in elements:
            res.append(self.get_repo(src))
        return sorted(res, key=operator.attrgetter("src"))

    def get_url(self, src: str) -> str:
        repo = self.get_repo(src)
        return repo.url

    def get_repo(self, src: str) -> tsrc.Repo:
        for repo in self._repos:
            if repo.src == src:
                return repo
        raise RepoNotFound(src)


def load(manifest_path: Path) -> Manifest:
    gitlab_schema = {"url": str}
    copy_schema = {"src": str, schema.Optional("dest"): str}
    repo_schema = {
        "src": str,
        "url": str,
        schema.Optional("branch"): str,
        schema.Optional("copy"): [copy_schema],
        schema.Optional("sha1"): str,
        schema.Optional("tag"): str,
    }
    group_schema = {
        "repos": [str],
        schema.Optional("includes"): [str],
    }
    manifest_schema = schema.Schema({
        "repos": [repo_schema],
        schema.Optional("gitlab"): gitlab_schema,
        schema.Optional("groups"): {str: group_schema},
    })
    parsed = tsrc.config.parse_config_file(manifest_path, manifest_schema)
    parsed = ManifestConfig(parsed)  # type: ignore
    as_manifest_config = cast(ManifestConfig, parsed)
    res = Manifest()
    res.load(as_manifest_config)
    return res
