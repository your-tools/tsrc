""" Entry point for `tsrc log`. """

import argparse
from pathlib import Path
from typing import List

import cli_ui as ui

from tsrc.cli import (
    add_num_jobs_arg,
    add_repos_selection_args,
    add_workspace_arg,
    get_num_jobs,
    get_workspace_with_repos,
)
from tsrc.errors import Error, MissingRepo
from tsrc.executor import Outcome, Task, process_items
from tsrc.git import run_git_captured
from tsrc.repo import Repo


def configure_parser(subparser: argparse._SubParsersAction) -> None:
    parser = subparser.add_parser("log")
    add_workspace_arg(parser)
    add_repos_selection_args(parser)
    parser.add_argument(
        "--from", dest="from_ref", metavar="FROM", help="run `git log` from this ref"
    )
    parser.add_argument(
        "--to",
        dest="to_ref",
        default="HEAD",
        help="run `git log` until this ref",
    )
    add_num_jobs_arg(parser)
    parser.set_defaults(run=run)


class LogCollector(Task[Repo]):
    def __init__(self, workspace_path: Path, *, from_ref: str, to_ref: str) -> None:
        self.workspace_path = workspace_path
        self.from_ref = from_ref
        self.to_ref = to_ref

    def describe_item(self, item: Repo) -> str:
        return item.dest

    def describe_process_start(self, item: Repo) -> List[ui.Token]:
        return [item.dest]

    def describe_process_end(self, item: Repo) -> List[ui.Token]:
        return [ui.green, "ok", ui.reset, item.dest]

    def process(self, index: int, count: int, repo: Repo) -> Outcome:
        # We just need to compute a summary here with the log between
        # self.from_ref and self.to_ref
        #
        # Note: make sure that when there is no diff between
        # self.from_ref and self.to_ref, the summary is empty,
        # so that the repo is not shown by OutcomeCollection.print_summary()
        repo_path = self.workspace_path / repo.dest
        if not repo_path.exists():
            raise MissingRepo(repo.dest)

        # The main reason for the `git log` command to fail is if `self.from_ref` or
        # `self.to_ref` references are not found for the repo, so check for this case
        # explicitly
        rc, _ = run_git_captured(repo_path, "rev-parse", self.from_ref, check=False)
        if rc != 0:
            raise Error(f"{self.from_ref} not found")
        rc, _ = run_git_captured(repo_path, "rev-parse", self.to_ref, check=False)
        if rc != 0:
            raise Error(f"{self.to_ref} not found")

        colors = ["green", "reset", "yellow", "reset", "bold blue", "reset"]
        log_format = "%m {}%h{} - {}%d{} %s {}<%an>{}"
        log_format = log_format.format(*("%C({})".format(x) for x in colors))
        cmd = [
            "log",
            "--color=always",
            f"--pretty=format:{log_format}",
            f"{self.from_ref}...{self.to_ref}",
        ]
        rc, out = run_git_captured(repo_path, *cmd, check=True)
        if out:
            lines = [repo.dest, "-" * len(repo.dest), out]
            return Outcome.from_lines(lines)
        else:
            return Outcome.empty()


def run(args: argparse.Namespace) -> None:
    workspace = get_workspace_with_repos(args)
    num_jobs = get_num_jobs(args)
    from_ref = args.from_ref
    to_ref = args.to_ref
    repos = workspace.repos
    log_collector = LogCollector(workspace.root_path, from_ref=from_ref, to_ref=to_ref)
    collection = process_items(repos, log_collector, num_jobs=num_jobs)
    collection.print_summary()
    if collection.errors:
        ui.error("Error when collecting logs")
        collection.print_errors()
        raise LogCollectorFailed


class LogCollectorFailed(Error):
    pass
