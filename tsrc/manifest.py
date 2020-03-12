""" manifests for tsrc """

import operator
from typing import cast, Any, Dict, List, Optional  # noqa

from path import Path
import schema

import tsrc


class RepoNotFound(tsrc.Error):
    def __init__(self, src: str) -> None:
        super().__init__("No repo found in '%s'" % src)


class Manifest:
    def __init__(self) -> None:
        self._repos = []  # type: List[tsrc.Repo]
        self.group_list = None  # type:  Optional[tsrc.GroupList[str]]

    def apply_config(self, config: Any) -> None:
        """ Apply config coming form the yaml file """
        # Note: we cannot just serialize the yaml file into the class,
        # because we need to convert the plain old dicts into
        # higher-level classes.
        self.copyfiles = []  # type: List[tsrc.Copy]
        repos_config = config["repos"]
        for repo_config in repos_config:
            self._handle_repo(repo_config)
            self._handle_copies(repo_config)

        groups_config = config.get("groups")
        self._handle_groups(groups_config)

    def _handle_repo(self, repo_config: Any) -> None:
        src = repo_config["src"]
        branch = repo_config.get("branch", "master")
        tag = repo_config.get("tag")
        sha1 = repo_config.get("sha1")
        url = repo_config.get("url")
        if url:
            origin = tsrc.Remote(name="origin", url=url)
            remotes = [origin]
        else:
            remotes = self._handle_remotes(repo_config)
        repo = tsrc.Repo(src=src, branch=branch, sha1=sha1, tag=tag, remotes=remotes)
        self._repos.append(repo)

    def _handle_remotes(self, repo_config: Any) -> List[tsrc.Remote]:
        remotes_config = repo_config.get("remotes")
        res = []
        if remotes_config:
            for remote_config in remotes_config:
                remote = tsrc.Remote(
                    name=remote_config["name"], url=remote_config["url"]
                )
                res.append(remote)
        return res

    def _handle_copies(self, repo_config: Any) -> None:
        if "copy" not in repo_config:
            return
        to_cp = repo_config["copy"]
        for item in to_cp:
            src = item["src"]
            dest = item.get("dest", src)
            copy = tsrc.Copy(repo_config["src"], src, dest)
            self.copyfiles.append(copy)

    def _handle_groups(self, groups_config: Any) -> None:
        elements = {repo.src for repo in self._repos}
        self.group_list = tsrc.GroupList(elements=elements)
        if not groups_config:
            return
        for name, group_config in groups_config.items():
            elements = group_config["repos"]
            includes = group_config.get("includes", [])
            self.group_list.add(name, elements, includes=includes)

    def get_repos(
        self, groups: Optional[List[str]] = None, all_: bool = False
    ) -> List[tsrc.Repo]:
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
        res = []
        for src in elements:
            res.append(self.get_repo(src))
        return sorted(res, key=operator.attrgetter("src"))

    def get_repo(self, src: str) -> tsrc.Repo:
        for repo in self._repos:
            if repo.src == src:
                return repo
        raise RepoNotFound(src)


def validate_repo(data: Any) -> None:
    copy_schema = {"src": str, schema.Optional("dest"): str}
    remote_schema = {"name": str, "url": str}
    repo_schema = schema.Schema(
        {
            "src": str,
            schema.Optional("branch"): str,
            schema.Optional("copy"): [copy_schema],
            schema.Optional("sha1"): str,
            schema.Optional("tag"): str,
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


def load(manifest_path: Path) -> Manifest:
    remote_git_server_schema = {"url": str}
    repo_schema = schema.Use(validate_repo)
    group_schema = {"repos": [str], schema.Optional("includes"): [str]}
    # Note: gitlab and github_enterprise_url keys are ignored,
    # and kept here only for backward compatibility reasons
    manifest_schema = schema.Schema(
        {
            "repos": [repo_schema],
            schema.Optional("gitlab"): remote_git_server_schema,
            schema.Optional("github_enterprise"): remote_git_server_schema,
            schema.Optional("groups"): {str: group_schema},
        }
    )
    parsed = tsrc.parse_config(manifest_path, manifest_schema)
    res = Manifest()
    res.apply_config(parsed)
    return res
