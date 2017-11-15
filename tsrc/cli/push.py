""" Entry point for tsrc push """

import re
import sys

import github3.models
import ui

import tsrc
import tsrc.config
import tsrc.github
import tsrc.git
import tsrc.cli


def get_token():
    config = tsrc.config.parse_tsrc_config()
    return config["auth"]["gitlab"]["token"]


def get_project_name(repo_path):
    rc, out = tsrc.git.run_git(repo_path, "remote", "get-url", "origin", raises=False)
    if rc != 0:
        ui.fatal("Could not get url of 'origin' remote:", out)
    repo_url = out
    return project_name_from_url(repo_url)


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


class PushAction():
    def __init__(self, args):
        self.args = args
        self.github_api = None
        self.source_branch = None
        self.target_branch = None
        self.project_name = None
        self.repo_path = None
        self.source_branch = None
        self.target_branch = None
        self.repository = None

    def main(self):
        self.prepare()
        self.push()
        self.handle_pull_request()

    def prepare(self):
        self.github_api = tsrc.github.login()

        self.repo_path = tsrc.git.get_repo_root()
        self.project_name = get_project_name(self.repo_path)
        organization, name = self.project_name.split("/")
        self.repository = self.github_api.repository(organization, name)

        current_branch = tsrc.git.get_current_branch(self.repo_path)
        self.source_branch = current_branch
        self.target_branch = self.args.target_branch

    def push(self):
        ui.info_2("Running git push")
        cmd = ["push", "-u", "origin", "%s:%s" % (self.source_branch, self.source_branch)]
        if self.args.force:
            cmd.append("--force")
        tsrc.git.run_git(self.repo_path, *cmd)

    def handle_pull_request(self):
        pull_request = self.ensure_pull_request()

        if self.args.accept:
            self.accept_pull_request(pull_request)

        ui.info(ui.green, "::",
                ui.reset, "See pull request at", pull_request.html_url)

    def find_opened_pull_request(self):
        for pull_request in self.repository.iter_pulls():
            if pull_request.head.ref == self.source_branch:
                if pull_request.state == "open":
                    return pull_request

    def create_pull_request(self):
        ui.info_2("Creating pull request", ui.ellipsis, end="")
        try:
            pull_request = self.repository.create_pull(
                self.source_branch,
                self.target_branch,
                self.source_branch
            )
            ui.info("done", ui.check)
        except github3.models.GitHubError as github_error:
            ui.info()
            ui.error(ui.red, "\nCould not create pull request")
            for error in github_error.errors:
                ui.info(ui.red, error["message"])
            sys.exit(1)
        return pull_request

    def ensure_pull_request(self):
        pull_request = self.find_opened_pull_request()
        if pull_request:
            ui.info_2("Found existing pull request: #%s" % pull_request.number)
            return pull_request
        else:
            return self.create_pull_request()


def main(args):
    push_action = PushAction(args)
    push_action.main()
