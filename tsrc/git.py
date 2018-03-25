""" git tools """


import os
import subprocess

from path import Path
import ui

import tsrc


class GitError(tsrc.Error):
    pass


class GitCommandError(GitError):
    def __init__(self, working_path, cmd, *, output=None):
        self.cmd = cmd
        self.working_path = working_path
        self.output = output
        message = "`git {cmd}` from {working_path} failed"
        message = message.format(cmd=" ".join(cmd), working_path=working_path)
        if output:
            message += "\n" + output
        super().__init__(message)


# pylint: disable=too-many-instance-attributes
class GitStatus:
    def __init__(self, working_path):
        self.working_path = working_path
        self.untracked = 0
        self.staged = 0
        self.not_staged = 0
        self.added = 0
        self.ahead = 0
        self.behind = 0
        self.dirty = False
        self.tag = None
        self.branch = None
        self.sha1 = None

    def update(self):
        self.update_sha1()
        self.update_branch()
        self.update_tag()
        self.update_remote_status()
        self.update_worktree_status()

    def update_sha1(self):
        self.sha1 = get_sha1(self.working_path, short=True)

    def update_branch(self):
        try:
            self.branch = get_current_branch(self.working_path)
        except GitError:
            pass

    def update_tag(self):
        try:
            self.tag = get_current_tag(self.working_path)
        except GitError:
            pass

    def update_remote_status(self):
        rc, ahead_rev = run_git_captured(
            self.working_path,
            "rev-list", "@{upstream}..HEAD",
            check=False
        )
        if rc == 0:
            self.ahead = len(ahead_rev.splitlines())

        rc, behind_rev = run_git_captured(
            self.working_path,
            "rev-list",
            "HEAD..@{upstream}",
            check=False
        )
        if rc == 0:
            self.behind = len(behind_rev.splitlines())

    def update_worktree_status(self):
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


class WorktreeNotFound(GitError):
    def __init__(self, working_path):
        super().__init__("'{}' is not inside a git repository".format(working_path))


def run_git(working_path, *cmd):
    """ Run git `cmd` in given `working_path`

    Raise GitCommandError if return code is non-zero.
    """
    git_cmd = list(cmd)
    git_cmd.insert(0, "git")

    ui.debug(ui.lightgray, working_path, "$", ui.reset, *git_cmd)
    returncode = subprocess.call(git_cmd, cwd=working_path)
    if returncode != 0:
        raise GitCommandError(working_path, cmd)


def run_git_captured(working_path, *cmd, check=True):
    """ Run git `cmd` in given `working_path`, capturing the output

    Return a tuple (returncode, output).

    Raise GitCommandError if return code is non-zero and check is True
    """
    git_cmd = list(cmd)
    git_cmd.insert(0, "git")
    options = dict()
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
        raise GitCommandError(working_path, cmd, output=out)
    return returncode, out


def get_sha1(working_path, short=False):
    cmd = ["rev-parse"]
    if short:
        cmd.append("--short")
    cmd.append("HEAD")
    _, output = run_git_captured(working_path, *cmd)
    return output


def get_current_branch(working_path):
    cmd = ("rev-parse", "--abbrev-ref", "HEAD")
    _, output = run_git_captured(working_path, *cmd)
    if output == "HEAD":
        raise GitError("Not an any branch")
    return output


def get_current_tag(working_path):
    cmd = ("tag", "--points-at", "HEAD")
    _, output = run_git_captured(working_path, *cmd)
    return output


def get_repo_root(working_path=None):
    if not working_path:
        working_path = Path(os.getcwd())
    cmd = ("rev-parse", "--show-toplevel")
    status, output = run_git_captured(working_path, *cmd, check=False)
    if status != 0:
        raise WorktreeNotFound(working_path)
    return Path(output)


def find_ref(repo, candidate_refs):
    """ Find the first reference that exists in the given repo """
    run_git(repo, "fetch", "--all", "--prune")
    for candidate_ref in candidate_refs:
        code, _ = run_git_captured(repo, "rev-parse", candidate_ref, check=False)
        if code == 0:
            return candidate_ref
    ref_list = ", ".join(candidate_refs)
    raise GitError("Could not find any of:", ref_list, "in repo", repo)


def reset(repo, ref):
    ui.info_2("Resetting", repo, "to", ref)
    run_git(repo, "reset", "--hard", ref)


def get_status(working_path):
    status = GitStatus(working_path)
    status.update()
    return status


def get_tracking_ref(working_path):
    rc, out = run_git_captured(
        working_path,
        "rev-parse", "--abbrev-ref",
        "--symbolic-full-name", "@{u}",
        check=False
    )
    if rc == 0:
        return out
    else:
        return None


def is_shallow(working_path):
    root = get_repo_root(working_path)
    return root.joinpath(".git/shallow").exists()
