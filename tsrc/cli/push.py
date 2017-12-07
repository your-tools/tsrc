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
        self.service = None
        self.tracking_ref = None
        self.read_working_path(working_path=working_path)

    def read_working_path(self, working_path=None):
        self.path = tsrc.git.get_repo_root(working_path=working_path)
        self.current_branch = tsrc.git.get_current_branch(self.path)
        rc, out = tsrc.git.run_git(self.path, "remote", "get-url", "origin", raises=False)
        if rc == 0:
            self.url = out
        if not self.url:
            return
        self.tracking_ref = tsrc.git.get_tracking_ref(self.path)
        self.project_name = project_name_from_url(self.url)
        self.service = service_from_url(self.url)


class PushAction(metaclass=abc.ABCMeta):
    def __init__(self, repository_info, args):
        self.args = args
        self.repository_info = repository_info

    @property
    def repo_path(self):
        return self.repository_info.path

    @property
    def tracking_ref(self):
        return self.repository_info.tracking_ref

    @property
    def remote_name(self):
        if not self.tracking_ref:
            return None
        return self.tracking_ref.split("/", maxsplit=1)[0]

    @property
    def current_branch(self):
        return self.repository_info.current_branch

    @property
    def remote_branch(self):
        if not self.tracking_ref:
            return self.current_branch
        else:
            return self.tracking_ref.split("/", maxsplit=1)[1]

    @property
    def target_branch(self):
        return self.args.target_branch

    @property
    def project_name(self):
        return self.repository_info.project_name

    @abc.abstractmethod
    def setup_service(self):
        pass

    @abc.abstractmethod
    def post_push(self):
        pass

    def push(self):
        ui.info_2("Running git push")
        remote_name = self.remote_name or "origin"
        if self.args.push_spec:
            push_spec = self.args.push_spec
        else:
            push_spec = "%s:%s" % (self.current_branch, self.remote_branch)
        cmd = ["push", "-u", remote_name, push_spec]
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
