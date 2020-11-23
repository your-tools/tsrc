""" Entry point for `tsrc log`. """

from typing import Any

import cli_ui as ui
from argh import arg

import tsrc
from tsrc.cli import repos_action, repos_arg


@repos_arg
@repos_action
@arg("--from", dest="from", metavar="FROM", help="from ref")  # type: ignore
@arg("--to", help="to ref")  # type: ignore
def log(workspace: tsrc.Workspace, **kwargs: Any) -> None:
    """ show a combined git log for several repositories """
    from_: str = kwargs["from"]
    to: str = kwargs["to"] or "HEAD"

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
            f"{from_}...{to}",
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
