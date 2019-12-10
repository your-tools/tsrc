""" Entry point for tsrc push """

import argparse
from typing import Optional

import cli_ui as ui

from tsrc.cli.push import RepositoryInfo
from tsrc.github_client.interface import Client, PullRequest


class PullRequestProcessor:
    def __init__(
        self, repository_info: RepositoryInfo, args: argparse.Namespace, client: Client
    ) -> None:
        self.repository_info = repository_info
        self.args = args
        self.client = client
        project_name = repository_info.project_name
        owner, name = project_name.split("/")
        self.repository = self.client.get_repository(owner, name)

    def process(self) -> None:
        pull_request = self.ensure_pull_request()
        if self.args.close:
            ui.info_2(
                "Closing pull request", ui.bold, pull_request.get_short_description()
            )
            pull_request.close()
            return

        base = None
        requested_target_branch = self.args.target_branch
        if requested_target_branch:
            base = requested_target_branch
            ui.info_3("Updating pull request with base:", ui.bold, base)

        title = None
        requested_title = self.args.title
        if requested_title:
            title = requested_title
            ui.info_3("Updating pull request with title", ui.bold, title)

        pull_request.update(base=base, title=title)

        requested_reviewers = self.args.reviewers
        if requested_reviewers:
            message = ["Requesting review from", ", ".join(requested_reviewers)]
            ui.info_2(*message)
            pull_request.request_reviewers(requested_reviewers)

        requested_assignee = self.args.assignee
        if requested_assignee:
            ui.info_2("Assigning to", requested_assignee)
            pull_request.assign(requested_assignee)

        if self.args.merge:
            ui.info_2("Merging", ui.bold, pull_request.get_short_description())
            pull_request.merge()

        ui.info(
            ui.green, "::", ui.reset, "See pull request at", pull_request.get_html_url()
        )

    def find_opened_pull_request(self) -> Optional[PullRequest]:
        remote_branch = self.repository_info.remote_branch
        pull_requests = self.repository.find_pull_requests(
            state="open", head=remote_branch
        )
        if pull_requests:
            return pull_requests[0]
        else:
            return None

    def create_pull_request(self) -> PullRequest:
        ui.info_2("Creating pull request")
        remote_branch = self.repository_info.remote_branch
        title = self.args.title or remote_branch
        head = remote_branch
        requested_target_branch = self.args.target_branch
        if requested_target_branch:
            base = requested_target_branch
        else:
            base = self.repository.get_default_branch()
        pull_request = self.repository.create_pull_request(
            title=title, head=head, base=base
        )
        return pull_request

    def ensure_pull_request(self) -> PullRequest:
        pull_request = self.find_opened_pull_request()
        if pull_request:
            ui.info_2(
                "Found existing pull request",
                ui.bold,
                pull_request.get_short_description(),
            )
            return pull_request
        else:
            return self.create_pull_request()


def post_push(args: argparse.Namespace, repository_info: RepositoryInfo) -> None:
    from tsrc.github_client.api_client import GitHubApiClient

    client = GitHubApiClient()
    review_proccessor = PullRequestProcessor(repository_info, args, client)
    review_proccessor.process()
