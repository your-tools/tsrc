""" Common code for push to GitHub or GitLab """

import abc
import argparse
import importlib
import re
from typing import cast, Iterable, Optional
from urllib.parse import urlparse

import attr
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


@attr.s(frozen=True)
class RepositoryInfo:
    project_name = attr.ib()  # type: str
    url = attr.ib()  # type: str
    path = attr.ib()  # type: Path
    current_branch = attr.ib()  # type: str
    service = attr.ib()  # type: str
    tracking_ref = attr.ib()  # type: Optional[str]
    repository_login_url = attr.ib()  # type: Optional[str]

    @classmethod
    def read(cls, working_path: Path, *, workspace: tsrc.Workspace) -> "RepositoryInfo":
        repo_path = tsrc.git.get_repo_root(working_path=working_path)
        current_branch = tsrc.git.get_current_branch(repo_path)
        tracking_ref = tsrc.git.get_tracking_ref(repo_path)

        # TODO: we should know the name of the remote at this point,
        # no need to hard-code 'origin'!
        rc, out = tsrc.git.run_captured(
            repo_path, "remote", "get-url", "origin", check=False
        )
        if rc == 0:
            url = out
        if not url:
            raise NoRemoteConfigured(repo_path, "origin")

        project_name = project_name_from_url(url)
        service = service_from_url(url=url, workspace=workspace)

        if service == "gitlab":
            repository_login_url = workspace.get_gitlab_url()
        elif service == "github_enterprise":
            repository_login_url = workspace.get_github_enterprise_url()
        else:
            repository_login_url = None

        return cls(
            project_name=project_name,
            url=url,
            path=repo_path,
            current_branch=current_branch,
            service=service,
            tracking_ref=tracking_ref,
            repository_login_url=repository_login_url,
        )


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

    repository_info = RepositoryInfo.read(Path.getcwd(), workspace=workspace)
    service_name = repository_info.service
    module = importlib.import_module("tsrc.cli.push_%s" % service_name)
    push_action = module.PushAction(repository_info, args)  # type: ignore
    push_action.execute()


class NoRemoteConfigured(tsrc.Error):
    def __init__(self, path: Path, name: str):
        message = "No remote named %s found in %s" % (name, path)
        super().__init__(message)
