""" Entry point for tsrc push """

import sys

import github3.models
import ui

import tsrc
import tsrc.config
import tsrc.github
import tsrc.cli.push


class PushAction(tsrc.cli.push.PushAction):
    def __init__(self, repository_info, args, github_api=None):
        super().__init__(repository_info, args)
        self.github_api = github_api
        self.repository = None
        self.pull_request = None

    def setup_service(self):
        if not self.github_api:
            self.github_api = tsrc.github.login()
        owner, name = self.project_name.split("/")
        self.repository = self.github_api.repository(owner, name)

    def post_push(self):
        self.pull_request = self.ensure_pull_request()

        if self.args.reviewers:
            message = ["Requesting review from", ", ".join(self.args.reviewers)]
            owner, name = self.project_name.split("/")
            ui.info_2(*message)
            tsrc.github.request_reviewers(
                self.github_api, owner, name, self.pull_request.number,
                self.args.reviewers)

        if self.args.assignee:
            ui.info_2("Assigning to", self.args.assignee)
            self.assign_pull_request()

        if self.args.merge:
            self.merge_pull_request()

        ui.info(ui.green, "::",
                ui.reset, "See pull request at", self.pull_request.html_url)

    def find_opened_pull_request(self):
        for pull_request in self.repository.iter_pulls():
            if pull_request.head.ref == self.remote_branch:
                if pull_request.state == "open":
                    return pull_request

    def create_pull_request(self):
        ui.info_2("Creating pull request", ui.ellipsis, end="")
        title = self.args.title or self.remote_branch
        try:
            pull_request = self.repository.create_pull(
                title,
                self.target_branch,
                self.remote_branch
            )
            ui.info("done", ui.check)
        except github3.models.GitHubError as github_error:
            ui.info()
            ui.error(ui.red, "\nCould not create pull request")
            for error in github_error.errors:
                ui.info(ui.red, error["message"])
            sys.exit(1)
        return pull_request

    def merge_pull_request(self):
        ui.info_2("Merging #", self.pull_request.number)
        self.pull_request.merge()

    def ensure_pull_request(self):
        pull_request = self.find_opened_pull_request()
        if pull_request:
            ui.info_2("Found existing pull request: #%s" % pull_request.number)
            return pull_request
        else:
            return self.create_pull_request()

    def assign_pull_request(self):
        issue = self.github_api.issue(
            self.repository.owner,
            self.repository.name,
            self.pull_request.number
        )
        issue.assign(self.args.assignee)
