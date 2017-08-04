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
            repo_url = repo_config["url"]
            repo_src = repo_config["src"]
            repo_branch = repo_config.get("branch", "master")
            repo = tsrc.Repo(url=repo_url, src=repo_src, branch=repo_branch)
            self.repos.append(repo)
            if "copy" in repo_config:
                to_cp = repo_config["copy"]
                for item in to_cp:
                    src = os.path.join(repo_src, item["src"])
                    self.copyfiles.append((src, item["dest"]))

    def get_url(self, src):
        for repo in self.repos:
            if repo.src == src:
                return repo.url
        raise RepoNotFound(src)
