""" manifests for tsrc """

import os

import schema

import tsrc
import tsrc.config


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
        schema.Optional("fixed_ref"): str,
    }
    manifest_schema = schema.Schema({
        schema.Optional("gitlab"): gitlab_schema,
        "repos": [repo_schema]
    })
    parsed = tsrc.config.parse_config_file(manifest_path, manifest_schema)
    res = Manifest()
    res.load(parsed)
    return res


class Manifest():
    def __init__(self):
        self.repos = list()      # repos to clone
        self.copyfiles = list()  # files to copy
        self.gitlab = dict()

    def load(self, data):
        self.copyfiles = list()
        self.gitlab = data.get("gitlab")
        repos = data.get("repos") or list()
        for repo_config in repos:
            url = repo_config["url"]
            src = repo_config["src"]
            branch = repo_config.get("branch", "master")
            fixed_ref = repo_config.get("fixed_ref")
            repo = tsrc.Repo(url=url, src=src, branch=branch,
                             fixed_ref=fixed_ref)
            self.repos.append(repo)

            self._handle_copies(repo_config)

    def _handle_copies(self, repo_config):
        if "copy" not in repo_config:
            return
        to_cp = repo_config["copy"]
        for item in to_cp:
            src_copy = item["src"]
            dest_copy = item.get("dest", src_copy)
            src_copy = os.path.join(repo_config["src"], src_copy)
            self.copyfiles.append((src_copy, dest_copy))

    def get_url(self, src):
        for repo in self.repos:
            if repo.src == src:
                return repo.url
        raise RepoNotFound(src)
