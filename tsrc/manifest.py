""" manifests for tsrc """

import operator
import os

import schema

import tsrc
import tsrc.config
import tsrc.groups


class RepoNotFound(tsrc.Error):
    def __init__(self, src):
        super().__init__("No repo found in '%s'" % src)


def load(manifest_path):
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
    res = Manifest()
    res.load(parsed)
    return res


class Manifest():
    def __init__(self):
        self._repos = list()
        self.copyfiles = list()
        self.gitlab = dict()
        self.group_list = None

    def load(self, config):
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

    def _handle_copies(self, repo_config):
        if "copy" not in repo_config:
            return
        to_cp = repo_config["copy"]
        for item in to_cp:
            src_copy = item["src"]
            dest_copy = item.get("dest", src_copy)
            src_copy = os.path.join(repo_config["src"], src_copy)
            self.copyfiles.append((src_copy, dest_copy))

    def _handle_groups(self, config):
        elements = set([repo.src for repo in self._repos])
        self.group_list = tsrc.groups.GroupList(elements=elements)
        groups_config = config.get("groups", dict())
        for name, group_config in groups_config.items():
            elements = set(group_config["repos"])
            includes = set(group_config.get("includes", list()))
            self.group_list.add(name, elements, includes=includes)

    def get_repos(self, groups=None, all_=False):
        if all_:
            return self._repos

        if not groups:
            if self._has_default_group():
                return self._get_repos_in_groups(["default"])
            else:
                return self._repos

        return self._get_repos_in_groups(groups)

    def _has_default_group(self):
        return self.group_list.get_group("default") is not None

    def _get_repos_in_groups(self, groups):
        elements = self.group_list.get_elements(groups=groups)
        res = list()
        for src in elements:
            res.append(self.get_repo(src))
        return sorted(res, key=operator.attrgetter("src"))

    def get_url(self, src):
        repo = self.get_repo(src)
        return repo.url

    def get_repo(self, src):
        for repo in self._repos:
            if repo.src == src:
                return repo
        raise RepoNotFound(src)
