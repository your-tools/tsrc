import argparse

from tsrc.cli.push import RepositoryInfo
from tsrc.cli.push_github import PullRequestProcessor


def post_push(args: argparse.Namespace, repository_info: RepositoryInfo) -> None:
    from tsrc.github_client.api_client import GitHubApiClient

    client = GitHubApiClient(enterprise_url=repository_info.login_url)

    review_proccessor = PullRequestProcessor(repository_info, args, client)
    review_proccessor.process()
