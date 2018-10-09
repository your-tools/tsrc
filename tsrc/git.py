""" git tools """


import os
import subprocess
from typing import Any, Dict, Iterable, Tuple, Optional  # noqa

from path import Path
import ui

import tsrc


class Error(tsrc.Error):
    pass


class CommandError(Error):
    def __init__(
            self, working_path: Path, cmd: Iterable[str], *,
            output: Optional[str] = None) -> None:
        self.cmd = cmd
        self.working_path = working_path
        self.output = output
        message = "`git {cmd}` from {working_path} failed"
        message = message.format(cmd=" ".join(cmd), working_path=working_path)
        if output:
            message += "\n" + output
        super().__init__(message)


class Status:
    def __init__(self, working_path: Path) -> None:
        self.working_path = working_path
        self.untracked = 0
        self.staged = 0
        self.not_staged = 0
        self.added = 0
        self.ahead = 0
        self.behind = 0
        self.dirty = False
        self.tag = None  # type: Optional[str]
        self.branch = None  # type: Optional[str]
        self.sha1 = None   # type: Optional[str]

    def update(self) -> None:
        self.update_sha1()
        self.update_branch()
        self.update_tag()
        self.update_remote_status()
        self.update_worktree_status()

    def update_sha1(self) -> None:
        self.sha1 = get_sha1(self.working_path, short=True)

    def update_branch(self) -> None:
        try:
            self.branch = get_current_branch(self.working_path)
        except Error:
            pass

    def update_tag(self) -> None:
        try:
            self.tag = get_current_tag(self.working_path)
        except Error:
            pass

    def update_remote_status(self) -> None:
        rc, ahead_rev = run_captured(
            self.working_path,
            "rev-list", "@{upstream}..HEAD",
            check=False
        )
        if rc == 0:
            self.ahead = len(ahead_rev.splitlines())

        rc, behind_rev = run_captured(
            self.working_path,
            "rev-list",
            "HEAD..@{upstream}",
            check=False
        )
        if rc == 0:
            self.behind = len(behind_rev.splitlines())

    def update_worktree_status(self) -> None:
        _, out = run_captured(self.working_path, "status", "--porcelain")

        for line in out.splitlines():
            if line.startswith("??"):
                self.untracked += 1
                self.dirty = True
            if line.startswith(" M"):
                self.staged += 1
                self.dirty = True
            if line.startswith(" .M"):
                self.not_staged += 1
                self.dirty = True
            if line.startswith("A "):
                self.added += 1
                self.dirty = True


class WorktreeNotFound(Error):
    def __init__(self, working_path: Path) -> None:
        super().__init__("'{}' is not inside a git repository".format(working_path))


def run(working_path: Path, *cmd: str) -> None:
    """ Run git `cmd` in given `working_path`

    Raise GitCommandError if return code is non-zero.
    """
    git_cmd = list(cmd)
    git_cmd.insert(0, "git")

    ui.debug(ui.lightgray, working_path, "$", ui.reset, *git_cmd)
    returncode = subprocess.call(git_cmd, cwd=working_path)
    if returncode != 0:
        raise CommandError(working_path, cmd)


def run_captured(working_path: Path, *cmd: str, check: bool = True) -> Tuple[int, str]:
    """ Run git `cmd` in given `working_path`, capturing the output

    Return a tuple (returncode, output).

    Raise GitCommandError if return code is non-zero and check is True
    """
    git_cmd = list(cmd)
    git_cmd.insert(0, "git")
    options = dict()  # type: Dict[str, Any]
    options["stdout"] = subprocess.PIPE
    options["stderr"] = subprocess.STDOUT

    ui.debug(ui.lightgray, working_path, "$", ui.reset, *git_cmd)
    process = subprocess.Popen(git_cmd, cwd=working_path, **options)
    out, _ = process.communicate()
    out = out.decode("utf-8")
    if out.endswith('\n'):
        out = out.strip('\n')
    returncode = process.returncode
    ui.debug(ui.lightgray, "[%i]" % returncode, ui.reset, out)
    if check and returncode != 0:
        raise CommandError(working_path, cmd, output=out)
    return returncode, out


def get_sha1(working_path: Path, short: bool = False, ref: str="HEAD") -> str:
    cmd = ["rev-parse"]
    if short:
        cmd.append("--short")
    cmd.append(ref)
    _, output = run_captured(working_path, *cmd)
    return output


def get_current_branch(working_path: Path) -> str:
    cmd = ("rev-parse", "--abbrev-ref", "HEAD")
    _, output = run_captured(working_path, *cmd)
    if output == "HEAD":
        raise Error("Not an any branch")
    return output


def get_current_tag(working_path: Path) -> str:
    cmd = ("tag", "--points-at", "HEAD")
    _, output = run_captured(working_path, *cmd)
    return output


def get_repo_root(working_path: Optional[Path] = None) -> Path:
    if not working_path:
        working_path = Path(os.getcwd())
    cmd = ("rev-parse", "--show-toplevel")
    status, output = run_captured(working_path, *cmd, check=False)
    if status != 0:
        raise WorktreeNotFound(working_path)
    return Path(output)


def find_ref(repo: Path, candidate_refs: Iterable[str]) -> str:
    """ Find the first reference that exists in the given repo """
    run(repo, "fetch", "--all", "--prune")
    for candidate_ref in candidate_refs:
        code, _ = run_captured(repo, "rev-parse", candidate_ref, check=False)
        if code == 0:
            return candidate_ref
    ref_list = ", ".join(candidate_refs)
    raise Error("Could not find any of:", ref_list, "in repo", repo)


def reset(repo: Path, ref: str) -> None:
    ui.info_2("Resetting", repo, "to", ref)
    run(repo, "reset", "--hard", ref)


def get_status(working_path: Path) -> Status:
    status = Status(working_path)
    status.update()
    return status


def get_tracking_ref(working_path: Path) -> Optional[str]:
    rc, out = run_captured(
        working_path,
        "rev-parse", "--abbrev-ref",
        "--symbolic-full-name", "@{upstream}",
        check=False
    )
    if rc == 0:
        return out
    else:
        return None


def is_shallow(working_path: Path) -> bool:
    root = get_repo_root(working_path)
    res = (root / ".git/shallow").exists()  # type: bool
    return res
