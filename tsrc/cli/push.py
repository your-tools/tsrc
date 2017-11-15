""" Common code for push to GitHub or GitLab """

import abc
import importlib
import re

import ui

import tsrc.git


def service_from_url(url):
    """
    >>> service_from_url("git@github.com:foo/bar")
    'github'
    >>> service_from_url("git@gitlab.local:foo/bar")
    'gitlab'

    """
    if url.startswith("git@github.com"):
        return "github"
    else:
        return "gitlab"


def project_name_from_url(url):
    """
    >>> project_name_from_url('git@example.com:foo/bar.git')
    'foo/bar'
    >>> project_name_from_url('ssh://git@example.com:8022/foo/bar.git')
    'foo/bar'

    """
    # split everthing that is separated by a colon or a slash
    parts = re.split("[:/]", url)
    # join the last two parts
    res = "/".join(parts[-2:])
    # remove last `.git`
    if res.endswith(".git"):
        res = res[:-4]
    return res


# pylint: disable=too-few-public-methods
class RepositoryInfo:
    def __init__(self, working_path=None):
        self.project_name = None
        self.url = None
        self.path = None
        self.current_branch = None
        self.read_working_path(working_path=working_path)
        self.service = None

    def read_working_path(self, working_path=None):
        self.path = tsrc.git.get_repo_root(working_path=working_path)
        self.current_branch = tsrc.git.get_current_branch(self.path)
        rc, out = tsrc.git.run_git(self.path, "remote", "get-url", "origin", raises=False)
        if rc == 0:
            self.url = out
        if not self.url:
            return
        self.project_name = project_name_from_url(self.url)
        self.service = service_from_url(self.url)


class PushAction(metaclass=abc.ABCMeta):
    def __init__(self, repository_info, args):
        self.args = args
        self.repo_path = None
        self.source_branch = None
        self.target_branch = None
        self._read_repository_info(repository_info)

    def _read_repository_info(self, repository_info):
        self.repo_path = repository_info.path
        self.project_name = repository_info.project_name
        self.source_branch = repository_info.current_branch
        self.target_branch = self.args.target_branch

    @abc.abstractmethod
    def setup_service(self):
        pass

    @abc.abstractmethod
    def post_push(self):
        pass

    def push(self):
        ui.info_2("Running git push")
        cmd = ["push", "-u", "origin", "%s:%s" % (self.source_branch, self.source_branch)]
        if self.args.force:
            cmd.append("--force")
        tsrc.git.run_git(self.repo_path, *cmd)

    def execute(self):
        self.setup_service()
        self.push()
        self.post_push()


def main(args):
    repository_info = RepositoryInfo()
    service_name = repository_info.service
    module = importlib.import_module("tsrc.cli.push_%s" % service_name)
    push_action = module.PushAction(repository_info, args)
    push_action.execute()
