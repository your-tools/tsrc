"""
Repo Grabber

allows 'dump-manifest' to paralelise GIT operations
on single Path of possible Repo.
"""

from pathlib import Path
from typing import List, Optional, Union

import cli_ui as ui

from tsrc.executor import Outcome, Task
from tsrc.git import GitStatus, is_git_repository
from tsrc.git_remote import GitRemote
from tsrc.repo import Repo


class RepoGrabber(Task[Repo]):
    """
    Implements a Task that check and obtain Repo from Path
    """

    def __init__(self, common_path: Union[List[str], None]) -> None:
        self.common_path = common_path
        self.repos: List[Repo] = []  # these are our output data

    def describe_item(self, item: Repo) -> str:
        return item.dest

    def describe_process_start(self, item: Repo) -> List[ui.Token]:
        return [item.dest]

    def describe_process_end(self, item: Repo) -> List[ui.Token]:
        return [ui.green, "ok", ui.reset, item.dest]

    def process(self, index: int, count: int, repo: Repo) -> Outcome:

        # we need actual Path (as Workspace Path may not be present here)
        repo_path: Optional[Path] = repo._grabbed_from_path
        if repo_path:
            if is_git_repository(repo_path) is False:
                return Outcome.empty()

            # obtain local GIT data
            gits = GitStatus(repo_path)
            gits.update()

            # obtain remote GIT data as well
            gitr = GitRemote(repo_path, repo.branch)
            gitr.update()
            if not gitr.remotes:
                # report missing remotes as such manifest will have litle meaning
                # in case we will want to use it later for synchronization
                ui.warning(f"No remote found for: '{repo.dest}' (path: '{repo_path}')")

            # we are now ready to create full Repo
            self.repos.append(
                Repo(
                    dest=repo.dest,
                    branch=gits.branch,
                    keep_branch=True,  # save empty branch if it is empty
                    is_default_branch=False,
                    orig_branch=gits.branch,
                    sha1=gits.sha1,
                    tag=gits.tag,
                    remotes=gitr.remotes,
                )
            )

        return Outcome.empty()
