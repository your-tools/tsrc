""" git tools """

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import cli_ui as ui

from tsrc.errors import Error

UP = ui.Symbol("↑", "+").as_string
DOWN = ui.Symbol("↓", "-").as_string


class GitError(Error):
    pass


class GitCommandError(GitError):
    def __init__(
        self,
        working_path: Path,
        cmd: Iterable[str],
        *,
        output: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        self.cmd = cmd
        self.working_path = working_path
        self.output = output
        cmd_str = " ".join(cmd)
        message = f"`git {cmd_str}` from {working_path} failed"
        if output:
            message += "\n" + output
        if error:
            message += "\n" + error
        super().__init__(message)


class NoSuchWorkingPath(GitError):
    def __init__(self, path: Path) -> None:
        super().__init__(f"'{path}' does not exist")


class WorktreeNotFound(GitError):
    def __init__(self, working_path: Path) -> None:
        super().__init__(f"'{working_path}' is not inside a git repository")


def assert_working_path(path: Path) -> None:
    if not path.exists():
        raise NoSuchWorkingPath(path)


class GitBareStatus:
    """
    Represent a status of bare git repo

    WARNING: only limited functionality is implemented
    as only very few information is needed for related Use-Case
    """

    def __init__(self, working_path: Path, remote_name: str, remote_url: str) -> None:
        self.working_path = working_path
        self.remote_name = remote_name
        self.remote_url = remote_url
        self.branch: Optional[str] = None
        self.ahead = 0
        self.behind = 0
        self.is_upstreamed: bool = False
        self.is_ok: bool = True

    def update(self) -> None:
        self.update_branch()
        if not self.branch:
            return
        self.update_upstream()
        self.update_remote_status()

    def update_branch(self) -> None:
        try:
            self.branch = get_current_branch(self.working_path)
        except GitError:
            pass

    def update_upstream(self) -> None:
        if self.branch:

            # check if upstream is already set
            rc, is_upstr = run_git_captured(
                self.working_path,
                "rev-parse",
                "--symbolic-full-name",
                f"{self.branch}@{{u}}",
                check=False,
            )
            if rc == 0:
                self.is_upstreamed = True
                return

            # if we are here, than we need to take some measures
            # so to setting upstream will be possible

            # refresh remotes so setting upstream will be possible later
            run_git_captured(
                self.working_path, "remote", "remove", self.remote_name, check=False
            )
            run_git_captured(
                self.working_path,
                "remote",
                "add",
                self.remote_name,
                self.remote_url,
                check=False,
            )
            run_git_captured(
                self.working_path, "fetch", "--all", "--prune", check=False
            )

            # only set upstream if it is not set
            rc, _ = run_git_captured(
                self.working_path,
                "branch",
                self.branch,
                "--set-upstream-to",
                f"{self.remote_name}/{self.branch}",
                check=False,
            )
            if rc == 0:
                self.is_upstreamed = True

    def update_remote_status(self) -> None:
        rc, ahead_rev = run_git_captured(
            self.working_path, "rev-list", "@{upstream}..HEAD", check=False
        )
        if rc == 0:
            self.ahead = len(ahead_rev.splitlines())

        rc, behind_rev = run_git_captured(
            self.working_path, "rev-list", "HEAD..@{upstream}", check=False
        )
        if rc == 0:
            self.behind = len(behind_rev.splitlines())

    @staticmethod
    def commit_string(number: int) -> str:
        """Describe the number of commit with correct pluralization."""

        if number == 1:
            return "commit"
        else:
            return "commits"

    def describe_position(
        self,
        ljust: int = 0,
        m_sha1_full: Optional[str] = None,
    ) -> Tuple[List[ui.Token], List[ui.Token], int]:
        """Return a status looking like `↑2↓1` if the branch
        is 2 commits ahead and one commit behind its upstream,
        as a list of tokens suitable for `ui.info()`.

        The difference here is that we have to report issue
        if one is found, as some info about SHA1 commit
        should be put out there in any case
        """
        m_sha1: Optional[str] = None
        if m_sha1_full:
            m_sha1 = m_sha1_full[:7]

        res: List[ui.Token] = []
        able: List[ui.Token] = []
        if self.is_upstreamed is True and self.is_ok is True:
            if self.ahead != 0:
                n_commits = GitStatus.commit_string(self.ahead)
                ahead_desc = f"{UP}{self.ahead} {n_commits}"
                res += [ui.blue, ahead_desc.ljust(ljust), ui.reset]
                ljust -= len(ahead_desc)
                able += [ui.blue, f"~~ {m_sha1}", ui.reset]
            if self.behind != 0:
                n_commits = GitStatus.commit_string(self.behind)
                behind_desc = f"{DOWN}{self.behind} {n_commits}"
                res += [ui.blue, behind_desc.ljust(ljust), ui.reset]
                ljust -= len(behind_desc)
                able += [ui.blue, f"~~ {m_sha1}", ui.reset]
            if self.ahead == 0 and self.behind == 0:
                same_desc = "~~ commit"
                res += [ui.blue, same_desc.ljust(ljust), ui.reset]
                ljust -= len(same_desc)
                able += [ui.blue, f"~~ {m_sha1}", ui.reset]
        else:
            if m_sha1:
                wrong_desc = f"!! {m_sha1}"
            else:
                wrong_desc = "!! commit"
            res += [ui.red, wrong_desc.ljust(ljust), ui.reset]
            able += [ui.red, wrong_desc, ui.reset]
            ljust -= len(wrong_desc)
        return res, able, ljust


class GitStatus:
    """Represent a status of a git repo.

    Usage:
    >>> status = Status(repo_path)
    >>> status.update()
    """

    def __init__(self, working_path: Path) -> None:
        # Note: at this point no information is known, and all
        # attributes have their default value.
        self.empty = False
        self.working_path = working_path
        self.untracked = 0
        self.staged = 0
        self.not_staged = 0
        self.added = 0
        self.ahead = 0
        self.behind = 0
        self.dirty = False
        self.tag: Optional[str] = None
        self.branch: Optional[str] = None
        self.sha1: Optional[str] = None
        self.sha1_full: Optional[str] = None

    def update(self) -> None:
        # Try and gather as many information about the git repository as
        # possible.
        try:
            self.update_sha1()
        except GitCommandError:
            self.empty = True
            return
        self.update_branch()
        self.update_tag()
        self.update_remote_status()
        self.update_worktree_status()

    def update_sha1(self) -> None:
        self.sha1_full = get_sha1(self.working_path, short=False)
        self.sha1 = self.sha1_full[:7]

    def update_branch(self) -> None:
        try:
            self.branch = get_current_branch(self.working_path)
        except GitError:
            pass

    def update_tag(self) -> None:
        try:
            self.tag = get_current_tag(self.working_path)
        except GitError:
            pass

    def update_remote_status(self) -> None:
        rc, ahead_rev = run_git_captured(
            self.working_path, "rev-list", "@{upstream}..HEAD", check=False
        )
        if rc == 0:
            self.ahead = len(ahead_rev.splitlines())

        rc, behind_rev = run_git_captured(
            self.working_path, "rev-list", "HEAD..@{upstream}", check=False
        )
        if rc == 0:
            self.behind = len(behind_rev.splitlines())

    def update_worktree_status(self) -> None:
        _, out = run_git_captured(self.working_path, "status", "--porcelain")

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

    def describe(self) -> List[ui.Token]:
        """Return a list of tokens suitable for ui.info."""
        res: List[ui.Token] = []
        if self.empty:
            return [ui.red, "empty"]
        res += self.describe_branch()
        res += self.describe_position()
        res += self.describe_dirty()
        return res

    def describe_pre_branch(self) -> List[ui.Token]:
        res: List[ui.Token] = []
        if self.empty:
            return [ui.red, "empty"]
        return res

    def describe_branch(self) -> List[ui.Token]:
        res: List[ui.Token] = []
        if self.branch:
            res += [ui.green, self.branch, ui.reset]
        elif self.sha1:
            res += [ui.red, self.sha1, ui.reset]
        if self.tag:
            res += [ui.brown, "on", self.tag, ui.reset]
        return res

    def len_of_describe_branch(self) -> int:
        len_: int = 0
        if self.branch:
            len_ += len(self.branch)
        elif self.sha1:
            len_ += len(self.sha1)
        if self.tag:
            len_ += len(self.tag) + 4  # " on "
        return len_

    def describe_post_branch(self) -> List[ui.Token]:
        res: List[ui.Token] = []
        res += self.describe_position()
        res += self.describe_dirty()
        return res

    @staticmethod
    def commit_string(number: int) -> str:
        """Describe the number of commit with correct pluralization."""

        if number == 1:
            return "commit"
        else:
            return "commits"

    def describe_position(self) -> List[ui.Token]:
        """Return a status looking like `↑2↓1` if the branch
        is 2 commits ahead and one commit behind its upstream,
        as a list of tokens suitable for `ui.info()`.

        """
        res: List[ui.Token] = []
        if self.ahead != 0:
            n_commits = GitStatus.commit_string(self.ahead)
            ahead_desc = f"{UP}{self.ahead} {n_commits}"
            res += [ui.blue, ahead_desc, ui.reset]
        if self.behind != 0:
            n_commits = GitStatus.commit_string(self.behind)
            behind_desc = f"{DOWN}{self.behind} {n_commits}"
            res += [ui.blue, behind_desc, ui.reset]
        return res

    def describe_dirty(self) -> List[ui.Token]:
        """Add the `(dirty)` colored string if the repo is dirty."""
        res: List[ui.Token] = []
        if self.dirty:
            res += [ui.red, "(dirty)", ui.reset]
        return res


def get_git_cmd(*args: str) -> List[str]:
    git_cmd = ["git"]
    testing = os.environ.get("TSRC_TESTING")
    if testing:
        # We need to check that `tsrc` works well with submodules and we
        # need to use the file:// protocol during tests This is disabled
        # by default for security reasons, so only allow it when testing
        git_cmd = git_cmd + ["-c", "protocol.file.allow=always"]
    git_cmd += list(args)
    return git_cmd


def run_git(
    working_path: Path,
    *cmd: str,
    check: bool = True,
    show_output: bool = True,
    show_cmd: bool = True,
) -> None:
    """Run git `cmd` in given `working_path`.

    Raise GitCommandError if return code is non-zero and `check` is True.
    """
    git_cmd = get_git_cmd(*cmd)

    if show_cmd:
        ui.info(ui.blue, "$", ui.reset, *git_cmd)
    if show_output:
        process = subprocess.run(git_cmd, cwd=working_path, universal_newlines=True)
    else:
        process = subprocess.run(
            git_cmd,
            cwd=working_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    if process.returncode != 0 and check:
        raise GitCommandError(working_path, cmd, output=process.stdout)


def run_git_captured(
    working_path: Path, *cmd: str, check: bool = True
) -> Tuple[int, str]:
    """Run git `cmd` in given `working_path`, capturing the output.

    Return a tuple (returncode, output).

    Raise GitCommandError if return code is non-zero and check is True.
    """
    assert_working_path(working_path)
    git_cmd = get_git_cmd(*cmd)

    options: Dict[str, Any] = {}
    options["stdout"] = subprocess.PIPE
    options["stderr"] = subprocess.PIPE
    options["text"] = True

    ui.debug(ui.lightgray, working_path, "$", ui.reset, *git_cmd)
    process = subprocess.Popen(git_cmd, cwd=working_path, **options)
    out, err = process.communicate()
    if out.endswith("\n"):
        out = out.strip("\n")
    returncode = process.returncode
    ui.debug(ui.lightgray, "[", returncode, "]", ui.reset, out)
    if check and returncode != 0:
        raise GitCommandError(working_path, cmd, output=out, error=err)
    return returncode, out


def get_sha1(working_path: Path, short: bool = False, ref: str = "HEAD") -> str:
    cmd = ["rev-parse"]
    if short:
        cmd.append("--short")
    cmd.append(ref)
    _, output = run_git_captured(working_path, *cmd)
    return output


def get_current_branch(working_path: Path) -> str:
    cmd = ("rev-parse", "--abbrev-ref", "HEAD")
    _, output = run_git_captured(working_path, *cmd)
    if output == "HEAD":
        raise GitError("Not an any branch")
    return output


def get_current_tag(working_path: Path) -> str:
    cmd = ("tag", "--points-at", "HEAD")
    _, output = run_git_captured(working_path, *cmd)
    return output


def get_repo_root(working_path: Optional[Path] = None) -> Path:
    if not working_path:
        working_path = Path(os.getcwd())
    cmd = ("rev-parse", "--show-toplevel")
    status, output = run_git_captured(working_path, *cmd, check=False)
    if status != 0:
        raise WorktreeNotFound(working_path)
    return Path(output)


def find_ref(repo: Path, candidate_refs: Iterable[str]) -> str:
    """Find the first reference that exists in the given repo"""
    run_git(repo, "fetch", "--all", "--prune")
    for candidate_ref in candidate_refs:
        code, _ = run_git_captured(repo, "rev-parse", candidate_ref, check=False)
        if code == 0:
            return candidate_ref
    ref_list = ", ".join(candidate_refs)
    raise GitError("Could not find any of:", ref_list, "in repo", repo)


def git_reset(repo: Path, ref: str) -> None:
    ui.info_2("Resetting", repo, "to", ref)
    run_git(repo, "reset", "--hard", ref)


def get_git_status(working_path: Path) -> GitStatus:
    status = GitStatus(working_path)
    status.update()
    return status


def get_git_bare_status(
    working_path: Path, remote_name: str, remote_url: str
) -> GitBareStatus:
    bare_status = GitBareStatus(working_path, remote_name, remote_url)
    bare_status.update()
    return bare_status


def is_git_repository(working_path: Path) -> bool:
    if not working_path.is_dir():
        return False
    rc, _ = run_git_captured(working_path, "rev-parse", "--git-dir", check=False)
    return rc == 0


def get_tracking_ref(working_path: Path) -> Optional[str]:
    # fmt: off
    rc, out = run_git_captured(
        working_path,
        "rev-parse", "--abbrev-ref",
        "--symbolic-full-name", "@{upstream}",
        check=False
    )
    # fmt: on
    if rc == 0:
        return out
    else:
        return None


def is_shallow(working_path: Path) -> bool:
    root = get_repo_root(working_path)
    res = (root / ".git/shallow").exists()
    return res
