""" git tools """


import os
import subprocess

import path

from tsrc import ui
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


class WorktreeNotFound(GitError):
    def __init__(self, working_path):
        super().__init__("'{}' is not inside a git repository".format(working_path))


def run_git(working_path, *cmd, raises=True):
    """ Run git `cmd` in given `working_path`

    If `raises` is True and git return code is non zero, raise
    an exception. Otherwise, return a tuple (returncode, out)

    """
    git_cmd = list(cmd)
    git_cmd.insert(0, "git")
    options = dict()
    if not raises:
        options["stdout"] = subprocess.PIPE
        options["stderr"] = subprocess.STDOUT

    process = subprocess.Popen(git_cmd, cwd=working_path, **options)

    if raises:
        process.wait()
    else:
        out, _ = process.communicate()
        out = out.decode("utf-8")

    returncode = process.returncode
    if raises:
        if returncode != 0:
            raise GitCommandError(working_path, cmd)
    else:
        if out.endswith('\n'):
            out = out.strip('\n')
        return returncode, out


def get_current_branch(working_path):
    cmd = ("rev-parse", "--abbrev-ref", "HEAD")
    status, output = run_git(working_path, *cmd, raises=False)
    if status != 0:
        raise GitCommandError(working_path, cmd, output=output)

    return output


def get_current_ref(working_path):
    cmd = ("rev-parse", "HEAD")
    status, output = run_git(working_path, *cmd, raises=False)
    if status != 0:
        raise GitCommandError(working_path, cmd, output=output)

    return output


def get_repo_root():
    working_path = path.Path(os.getcwd())
    cmd = ("rev-parse", "--show-toplevel")
    status, output = run_git(working_path, *cmd, raises=False)
    if status != 0:
        raise WorktreeNotFound(working_path)
    return path.Path(output)


def is_dirty(working_path):
    status, _ = run_git(working_path, "diff-index", "--quiet", "HEAD", raises=False)
    return status != 0


def find_ref(repo, candidate_refs):
    """ Find the first reference that exists in the given repo """
    run_git(repo, "fetch", "--all", "--prune")
    for candidate_ref in candidate_refs:
        code, _ = run_git(repo, "rev-parse", candidate_ref, raises=False)
        if code == 0:
            return candidate_ref
    ref_list = ", ".join(candidate_refs)
    raise GitError("Could not find any of:", ref_list, "in repo", repo)


def reset(repo, ref):
    ui.info_2("Resetting", repo, "to", ref)
    run_git(repo, "reset", "--hard", ref)
