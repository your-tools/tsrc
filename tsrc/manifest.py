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
        self.clone_prefix = None

    def load(self, contents):
        self.copyfiles = list()
        parsed = ruamel.yaml.safe_load(contents) or dict()
        self.gitlab = parsed.get("gitlab")
        self.clone_prefix = parsed["clone_prefix"]

        repos = parsed.get("repos") or list()
        for repo in repos:
            repo_url = joinurl(self.clone_prefix, repo["name"])
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


def joinurl(prefix, name):
    res = None
    if os.path.exists(prefix):
        res = os.path.join(prefix, name)
    elif has_scheme(prefix):
        res = join_with(prefix, name, "/")
    else:
        # Assume simple ssh URL like git@host:path, or just host:path
        res = join_with(prefix, name, ":")
    if not res.endswith(".git"):
        res += ".git"
    return res


def join_with(prefix, name, joiner):
    if not prefix.endswith(joiner):
        prefix += joiner
    return prefix + name


def has_scheme(url):
    """
    >>> has_scheme('http://foo/bar')
    True
    >>> has_scheme('git+ssh://foo/bar')
    True
    >>> has_scheme('git@foo.com')
    False
    """
    return "://" in url
