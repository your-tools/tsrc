""" Common code for push to GitHub or GitLab """

from typing import Optional
import argparse
import importlib
import re
from urllib.parse import urlparse

import attr
from path import Path
import cli_ui as ui

import tsrc
import tsrc.git
import tsrc.cli


def service_from_url(url: str, *, manifest: tsrc.Manifest) -> Optional[str]:
    if url.startswith("git@github.com"):
        return "github"

    github_enterprise_url = manifest.github_enterprise_url
    if github_enterprise_url:
        github_domain = urlparse(github_enterprise_url).hostname
        if url.startswith("git@%s" % github_domain):
            return "github_enterprise"

    gitlab_url = manifest.gitlab_url
    if gitlab_url:
        gitlab_domain = urlparse(gitlab_url).hostname
        if url.startswith("git@%s" % gitlab_domain):
            return "gitlab"

    return None


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


@attr.s
class RepositoryInfo:
    project_name = attr.ib()  # type: str
    url = attr.ib()  # type: str
    path = attr.ib()  # type: Path
    remote_name = attr.ib()  # type: str
    current_branch = attr.ib()  # type: str
    service = attr.ib()  # type: Optional[str]
    tracking_ref = attr.ib()  # type: Optional[str]
    login_url = attr.ib()  # type: Optional[str]

    @classmethod
    def read(
        cls, working_path: Path, *, manifest: tsrc.Manifest, remote_name: str = "origin"
    ) -> "RepositoryInfo":
        repo_path = tsrc.git.get_repo_root(working_path=working_path)
        current_branch = tsrc.git.get_current_branch(repo_path)
        tracking_ref = tsrc.git.get_tracking_ref(repo_path)

        url = None
        rc, out = tsrc.git.run_captured(
            repo_path, "remote", "get-url", remote_name, check=False
        )
        if rc == 0:
            url = out
        if not url:
            raise NoRemoteConfigured(repo_path, remote_name)

        project_name = project_name_from_url(url)
        service = service_from_url(url, manifest=manifest)

        if service == "gitlab":
            login_url = manifest.gitlab_url
        elif service == "github_enterprise":
            login_url = manifest.github_enterprise_url
        else:
            login_url = None

        return cls(
            project_name=project_name,
            remote_name=remote_name,
            url=url,
            path=repo_path,
            current_branch=current_branch,
            service=service,
            tracking_ref=tracking_ref,
            login_url=login_url,
        )

    @property
    def remote_branch(self) -> str:
        if not self.tracking_ref:
            return self.current_branch
        else:
            return self.tracking_ref.split("/", maxsplit=1)[1]

    def update_tracking_ref(self, push_spec: str) -> None:
        self.tracking_ref = "{}/{}".format(self.remote_name, push_spec.split(":")[1])


def push(repository_info: RepositoryInfo, args: argparse.Namespace) -> None:
    remote_name = repository_info.remote_name
    if args.push_spec:
        push_spec = args.push_spec
    else:
        push_spec = "%s:%s" % (
            repository_info.current_branch,
            repository_info.remote_branch,
        )
    cmd = ["push", "-u", remote_name, push_spec]
    if args.force:
        cmd.append("--force")
    repo_path = repository_info.path
    ui.info_2("Running git", *cmd)
    tsrc.git.run(repo_path, *cmd)

    # We just used push with a "-u" so the repository_info needs
    # to be updated
    repository_info.update_tracking_ref(push_spec)


def main(args: argparse.Namespace) -> None:
    workspace = tsrc.cli.get_workspace(args)
    repository_info = RepositoryInfo.read(
        Path.getcwd(), manifest=workspace.get_manifest(), remote_name=args.origin
    )
    push(repository_info, args)
    service_name = repository_info.service
    if service_name:
        module = importlib.import_module("tsrc.cli.push_%s" % service_name)
        module.post_push(args, repository_info)  # type: ignore


class NoRemoteConfigured(tsrc.Error):
    def __init__(self, path: Path, name: str):
        message = "No remote named %s found in %s" % (name, path)
        super().__init__(message)
