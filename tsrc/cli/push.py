""" Common code for push to GitHub or GitLab """

import abc
import argparse
import importlib
import re
from typing import cast, Iterable, Optional
from urllib.parse import urlparse

from path import Path
import cli_ui as ui

import tsrc
import tsrc.git
import tsrc.cli


def service_from_url(url: str, workspace: tsrc.Workspace) -> str:
    if url.startswith("git@github.com"):
        return "github"

    github_enterprise_url = workspace.get_github_enterprise_url()
    if github_enterprise_url:
        github_domain = urlparse(github_enterprise_url).hostname
        if url.startswith("git@%s" % github_domain):
            return "github_enterprise"

    gitlab_url = workspace.get_gitlab_url()
    if gitlab_url:
        gitlab_domain = urlparse(gitlab_url).hostname
        if url.startswith("git@%s" % gitlab_domain):
            return "gitlab"

    return "git"


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
    def __init__(self, workspace: tsrc.Workspace, working_path: Path = None) -> None:
        self.project_name = None  # type: Optional[str]
        self.url = None  # type: Optional[str]
        self.path = None  # type: Optional[Path]
        self.current_branch = None  # type: Optional[str]
        self.service = None  # type: Optional[str]
        self.tracking_ref = None  # type: Optional[str]
        self.repository_login_url = None  # type: Optional[str]
        self.read_working_path(workspace=workspace, working_path=working_path)

    def read_working_path(
        self, workspace: tsrc.Workspace, working_path: Path = None
    ) -> None:
        self.path = tsrc.git.get_repo_root(working_path=working_path)
        self.current_branch = tsrc.git.get_current_branch(self.path)
        rc, out = tsrc.git.run_captured(
            self.path, "remote", "get-url", "origin", check=False
        )
        if rc == 0:
            self.url = out
        if not self.url:
            return
        self.tracking_ref = tsrc.git.get_tracking_ref(self.path)
        self.project_name = project_name_from_url(self.url)
        self.service = service_from_url(url=self.url, workspace=workspace)

        if self.service == "gitlab":
            self.repository_login_url = workspace.get_gitlab_url()
        elif self.service == "github_enterprise":
            self.repository_login_url = workspace.get_github_enterprise_url()


class PushAction(metaclass=abc.ABCMeta):
    def __init__(
        self, repository_info: RepositoryInfo, args: argparse.Namespace
    ) -> None:
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
    workspace = tsrc.cli.get_workspace(args)
    workspace.load_manifest()

    repository_info = RepositoryInfo(workspace)
    service_name = repository_info.service
    module = importlib.import_module("tsrc.cli.push_%s" % service_name)
    push_action = module.PushAction(repository_info, args)  # type: ignore
    push_action.execute()
