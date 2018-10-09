""" Common code for push to GitHub or GitLab """

import abc
import argparse
import importlib
import re
from typing import cast, Iterable, Optional

from path import Path
import ui

import tsrc
import tsrc.git


def service_from_url(url: str) -> str:
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


def project_name_from_url(url: str) -> str:
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


class RepositoryInfo:
    def __init__(self, working_path: Path = None) -> None:
        self.project_name = None  # type: Optional[str]
        self.url = None  # type: Optional[str]
        self.path = None  # type: Optional[Path]
        self.current_branch = None  # type: Optional[str]
        self.service = None  # type: Optional[str]
        self.tracking_ref = None  # type: Optional[str]
        self.read_working_path(working_path=working_path)

    def read_working_path(self, working_path: Path = None) -> None:
        self.path = tsrc.git.get_repo_root(working_path=working_path)
        self.current_branch = tsrc.git.get_current_branch(self.path)
        rc, out = tsrc.git.run_captured(self.path, "remote", "get-url", "origin", check=False)
        if rc == 0:
            self.url = out
        if not self.url:
            return
        self.tracking_ref = tsrc.git.get_tracking_ref(self.path)
        self.project_name = project_name_from_url(self.url)
        self.service = service_from_url(self.url)


class PushAction(metaclass=abc.ABCMeta):
    def __init__(self, repository_info: RepositoryInfo, args: argparse.Namespace) -> None:
        self.args = args
        self.repository_info = repository_info

    @property
    def repo_path(self) -> Path:
        return self.repository_info.path

    @property
    def tracking_ref(self) -> Optional[str]:
        return self.repository_info.tracking_ref

    @property
    def remote_name(self) -> Optional[str]:
        if not self.tracking_ref:
            return None
        return self.tracking_ref.split("/", maxsplit=1)[0]

    @property
    def current_branch(self) -> Optional[str]:
        return self.repository_info.current_branch

    @property
    def remote_branch(self) -> Optional[str]:
        if not self.tracking_ref:
            return self.current_branch
        else:
            return self.tracking_ref.split("/", maxsplit=1)[1]

    @property
    def requested_target_branch(self) -> Optional[str]:
        return cast(Optional[str], self.args.target_branch)

    @property
    def requested_title(self) -> Optional[str]:
        return cast(Optional[str], self.args.title)

    @property
    def requested_reviewers(self) -> Iterable[str]:
        return cast(Iterable[str], self.args.reviewers)

    @property
    def requested_assignee(self) -> Optional[str]:
        return cast(Optional[str], self.args.assignee)

    @property
    def project_name(self) -> Optional[str]:
        return self.repository_info.project_name

    @abc.abstractmethod
    def setup_service(self) -> None:
        pass

    @abc.abstractmethod
    def post_push(self) -> None:
        pass

    def push(self) -> None:
        ui.info_2("Running git push")
        remote_name = self.remote_name or "origin"
        if self.args.push_spec:
            push_spec = self.args.push_spec
        else:
            push_spec = "%s:%s" % (self.current_branch, self.remote_branch)
        cmd = ["push", "-u", remote_name, push_spec]
        if self.args.force:
            cmd.append("--force")
        tsrc.git.run(self.repo_path, *cmd)

    def execute(self) -> None:
        self.setup_service()
        self.push()
        self.post_push()


def main(args: argparse.Namespace) -> None:
    repository_info = RepositoryInfo()
    service_name = repository_info.service
    module = importlib.import_module("tsrc.cli.push_%s" % service_name)
    push_action = module.PushAction(repository_info, args)  # type: ignore
    push_action.execute()
