""" Entry point for tsrc log """

from typing import List, Optional

from argh import arg
from path import Path
import cli_ui as ui

import tsrc

from tsrc.cli import (
    with_workspace,
    with_groups,
    with_all_cloned,
    get_workspace,
    resolve_repos,
)


@with_workspace  # type: ignore
@with_groups  # type: ignore
@with_all_cloned  # type: ignore
@arg("--from", dest="from_", metavar="FROM", help="from ref")  # type: ignore
@arg("--to", help="to ref")  # type: ignore
def log(
    workspace_path: Optional[Path] = None,
    groups: Optional[List[str]] = None,
    all_cloned: bool = False,
    to: str = "",
    from_: str = "",
) -> None:
    """ show a combine git log for several repositories """
    workspace = get_workspace(workspace_path)
    workspace.repos = resolve_repos(workspace, groups=groups, all_cloned=all_cloned)
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
