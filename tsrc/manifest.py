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
        for repo in repos:
            repo_url = repo["url"]
            repo_src = repo["src"]
            self.repos.append((repo_src, repo_url))
            if "copy" in repo:
                to_cp = repo["copy"]
                for item in to_cp:
                    src = os.path.join(repo_src, item["src"])
                    self.copyfiles.append((src, item["dest"]))

    def get_url(self, src):
        for (repo_src, repo_url) in self.repos:
            if repo_src == src:
                return repo_url
        raise RepoNotFound(src)
