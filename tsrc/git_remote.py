"""
Git Remote

Collection of simple GIT remote tools
that can be called when additional checks
needs to be performed on special occasions.

This is pariculary useful for Manifest-related
checks.
"""

from pathlib import Path

from tsrc.git import run_git_captured


def remote_branch_exist(url: str, branch: str) -> int:
    """
    check if remote 'branch' exists
    'url' of repository needs to be provided
    any other return code but '0'
    should be considered an error
    """
    p = Path(".")
    rc, _ = run_git_captured(
        p,
        "ls-remote",
        "--exit-code",
        "--heads",
        url,
        f"refs/heads/{branch}",
        check=False,
    )
    return rc
