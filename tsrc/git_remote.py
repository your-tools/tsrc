"""
Git Remote

Collection of simple GIT remote tools
that can be called when additional checks
needs to be performed on special occasions.

This is pariculary useful for Manifest-related
checks.
"""

from pathlib import Path
from sys import platform
from typing import List, Tuple, Union
from urllib.parse import quote, urlparse

from tsrc.git import run_git_captured


def remote_urls_are_same(url_1: str, url_2: str) -> bool:
    """
    return True if provided URLs are the same
    """
    up_1 = urlparse(url_1)
    up_2 = urlparse(url_2)
    if up_1.scheme != "file" and up_2.scheme != "file":
        return (
            up_1.scheme == up_2.scheme
            and up_1.hostname == up_2.hostname  # noqa: W503
            and up_1.port == up_2.port  # noqa: W503
            and _norm_path(quote(up_1.path))  # noqa: W503
            == _norm_path(quote(up_2.path))  # noqa: W503
        )
    else:
        if platform.startswith("win"):
            return (
                up_1.scheme == up_2.scheme and up_1.netloc == up_2.netloc  # noqa: W503
            )
        else:
            return (
                up_1.scheme == up_2.scheme
                and up_1.netloc == up_2.netloc  # noqa: W503
                and up_1.hostname == up_2.hostname  # noqa: W503
                and _norm_path(quote(up_1.path))  # noqa: W503
                == _norm_path(quote(up_2.path))  # noqa: W503
            )


def _norm_path(path: str) -> str:
    ret: str = ""
    if path[0] == "/":
        ret += "/"
    u_seg: List[str] = []
    path_split = path.split("/")
    for seg in path_split:
        if seg != "":
            u_seg.append(seg)
    ret += "/".join(u_seg)
    return ret


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


def get_l_and_r_sha1_of_branch(
    w_r_path: Path,
    dest: str,
    branch: str,
) -> Tuple[Union[str, None], Union[str, None]]:
    """obtain local and remote SHA1 of given branch.
    This is useful when we need to check if we are exactly
    updated with remote down to the commit"""
    rc, l_b_sha = run_git_captured(
        w_r_path / dest,
        "rev-parse",
        "--verify",
        "HEAD",
        check=False,
    )
    if rc != 0:
        return None, None

    _, l_ref = run_git_captured(w_r_path / dest, "symbolic-ref", "-q", "HEAD")
    _, r_ref = run_git_captured(
        w_r_path / dest, "for-each-ref", "--format='%(upstream)'", l_ref
    )
    r_b_sha = None
    if rc == 0:
        tmp_r_ref = r_ref.split("/")
        this_remote = tmp_r_ref[2]
        _, r_b_sha = run_git_captured(
            w_r_path / dest,
            "ls-remote",
            "--exit-code",
            "--head",
            this_remote,
            l_ref,
            check=True,
        )
    if r_b_sha:
        return l_b_sha, r_b_sha.split()[0]
    else:
        return l_b_sha, None
