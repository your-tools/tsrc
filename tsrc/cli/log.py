""" Entry point for `tsrc log`. """

import argparse

import cli_ui as ui

import tsrc
from tsrc.cli import (
    add_repos_selection_args,
    add_workspace_arg,
    get_workspace_with_repos,
)


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
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> None:
    workspace = get_workspace_with_repos(args)
    all_ok = True
    for repo in workspace.repos:
        full_path = workspace.root_path / repo.dest
        if not full_path.exists():
            ui.info(ui.bold, repo.dest, ": ", ui.red, "error: missing repo", sep="")
            all_ok = False
            continue

        colors = ["green", "reset", "yellow", "reset", "bold blue", "reset"]
        log_format = "%m {}%h{} - {}%d{} %s {}<%an>{}"
        log_format = log_format.format(*("%C({})".format(x) for x in colors))
        cmd = [
            "log",
            "--color=always",
            f"--pretty=format:{log_format}",
            f"{args.from_ref}...{args.to_ref}",
        ]
        rc, out = tsrc.git.run_captured(full_path, *cmd, check=False)
        if rc != 0:
            all_ok = False
        if out:
            ui.info(ui.bold, repo.dest)
            ui.info(ui.bold, "-" * len(repo.dest))
            ui.info(out)
    if not all_ok:
        raise tsrc.Error()
