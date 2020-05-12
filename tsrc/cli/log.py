""" Entry point for tsrc log """

import argparse

import cli_ui as ui

import tsrc
import tsrc.cli


def main(args: argparse.Namespace) -> None:
    workspace = tsrc.cli.get_workspace_with_repos(args)
    all_ok = True
    for repo in workspace.repos:
        full_path = workspace.root_path / repo.src
        if not full_path.exists():
            ui.info(ui.bold, repo.src, ui.red, "error: missing")
            all_ok = False
            continue

        colors = ["green", "reset", "yellow", "reset", "bold blue", "reset"]
        log_format = "%m {}%h{} - {}%d{} %s {}<%an>{}"
        log_format = log_format.format(*("%C({})".format(x) for x in colors))
        cmd = [
            "log",
            "--color=always",
            f"--pretty=format:{log_format}",
            f"{args.from_}...{args.to}",
        ]
        rc, out = tsrc.git.run_captured(full_path, *cmd, check=False)
        if rc != 0:
            all_ok = False
        if out:
            ui.info(ui.bold, repo.src)
            ui.info(ui.bold, "-" * len(repo.src))
            ui.info(out)
    if not all_ok:
        raise tsrc.Error()
