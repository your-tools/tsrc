""" manifests for tsrc """
import os

import ruamel.yaml

import tsrc


class RepoNotFound(tsrc.Error):
    def __init__(self, src):
        super().__init__("No repo found in '%s'" % src)


# pylint: disable=too-few-public-methods
class Manifest():
    def __init__(self):
        self.repos = list()      # repos to clone
        self.copyfiles = list()  # files to copy
        self.gitlab = dict()

    def load(self, contents):
        self.copyfiles = list()
        parsed = ruamel.yaml.safe_load(contents) or dict()
        self.gitlab = parsed.get("gitlab")
        repos = parsed.get("repos") or list()
        for repo_config in repos:
            url = repo_config["url"]
            src = repo_config["src"]
            branch = repo_config.get("branch", "master")
            fixed_ref = repo_config.get("fixed_ref")
            repo = tsrc.Repo(url=url, src=src, branch=branch,
                             fixed_ref=fixed_ref)
            self.repos.append(repo)
            if "copy" in repo_config:
                to_cp = repo_config["copy"]
                for item in to_cp:
                    src_copy = os.path.join(src, item["src"])
                    dest_copy = item["dest"]
                    self.copyfiles.append((src_copy, dest_copy))

    def get_url(self, src):
        for repo in self.repos:
            if repo.src == src:
                return repo.url
        raise RepoNotFound(src)
