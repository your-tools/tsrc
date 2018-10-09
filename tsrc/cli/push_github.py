""" Entry point for tsrc push """

import argparse
import sys
from typing import Optional

import github3
from github3 import GitHub
from github3.pulls import PullRequest
import ui

import tsrc
import tsrc.github
from tsrc.cli.push import RepositoryInfo


class PushAction(tsrc.cli.push.PushAction):
    def __init__(self, repository_info: RepositoryInfo, args:
                 argparse.Namespace, github_api: Optional[GitHub] = None) -> None:
        super().__init__(repository_info, args)
        self.github_api = github_api
        self.repository = None
        self.pull_request = None

    def setup_service(self) -> None:
        if not self.github_api:
            self.github_api = tsrc.github.login()
        assert self.project_name
        owner, name = self.project_name.split("/")
        self.repository = self.github_api.repository(owner, name)

    def post_push(self) -> None:
        self.pull_request = self.ensure_pull_request()
        assert self.pull_request
        if self.args.close:
            ui.info_2("Closing merge request #%s" % self.pull_request.number)
            self.pull_request.close()
            return
        params = dict()
        if self.requested_target_branch:
            params["base"] = self.requested_target_branch

        if self.requested_title:
            params["title"] = self.requested_title

        self.pull_request.update(**params)

        if self.requested_reviewers:
            message = ["Requesting review from", ", ".join(self.requested_reviewers)]
            ui.info_2(*message)
            tsrc.github.request_reviewers(
                self.repository,
                self.pull_request.number,
                self.requested_reviewers
            )

        if self.requested_assignee:
            ui.info_2("Assigning to", self.requested_assignee)
            self.assign_pull_request()

        if self.args.merge:
            self.merge_pull_request()

        ui.info(ui.green, "::",
                ui.reset, "See pull request at", self.pull_request.html_url)

    def find_opened_pull_request(self) -> Optional[PullRequest]:
        assert self.repository
        for pull_request in self.repository.pull_requests():
            if pull_request.head.ref == self.remote_branch:
                if pull_request.state == "open":
                    return pull_request
        return None

    def create_pull_request(self) -> PullRequest:
        assert self.repository
        ui.info_2("Creating pull request", ui.ellipsis, end="")
        title = self.requested_title or self.remote_branch
        if self.requested_target_branch:
            target_branch = self.requested_target_branch
        else:
            target_branch = self.repository.default_branch
        try:
            pull_request = self.repository.create_pull(
                title,
                target_branch,
                self.remote_branch
            )
            ui.info("done", ui.check)
        except github3.GitHubError as github_error:
            ui.info()
            ui.error(ui.red, "\nCould not create pull request")
            for error in github_error.errors:
                ui.info(ui.red, error["message"])
            sys.exit(1)
        return pull_request

    def merge_pull_request(self) -> None:
        assert self.pull_request
        ui.info_2("Merging #", self.pull_request.number)
        self.pull_request.merge()

    def ensure_pull_request(self) -> PullRequest:
        pull_request = self.find_opened_pull_request()
        if pull_request:
            ui.info_2("Found existing pull request: #%s" % pull_request.number)
            return pull_request
        else:
            return self.create_pull_request()

    def assign_pull_request(self) -> None:
        assert self.pull_request
        issue = self.repository.issue(self.pull_request.number)
        issue.assign(self.requested_assignee)
