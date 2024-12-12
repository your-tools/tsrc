"""
Manifest Dumper - Helpers

helps Dumper to use unified dataclass
that can be processed across various of cases
and thus simplify already complex functions
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Union

import cli_ui as ui

from tsrc.repo import Remote, Repo
from tsrc.status_endpoint import CollectedStatuses, Status


@dataclass(frozen=True)
class ManifestRepoItem:
    branch: Optional[str] = None
    tag: Optional[str] = None
    sha1: Optional[str] = None
    empty: Optional[bool] = False
    ignore_submodules: Optional[bool] = False
    remotes: Optional[List[Remote]] = None
    groups_considered: Optional[bool] = False
    # TODO: implement test if required variables are set

    @property
    def clone_url(self) -> str:
        assert self.remotes
        return self.remotes[0].url


class MRISHelpers:
    def __init__(
        self,
        statuses: Optional[CollectedStatuses] = None,
        w_repos: Optional[List[Repo]] = None,  # Workspace's Repos
        repos: Optional[List[Repo]] = None,
    ) -> None:
        self.mris: Dict[str, ManifestRepoItem] = {}
        if bool(statuses) == bool(repos):
            return
        if statuses:
            self._statuses_to_mris(statuses, w_repos)
        if repos:
            self._repos_to_mris(repos)

    def _repo_to_mri(
        self,
        repo: Repo,
    ) -> ManifestRepoItem:
        return ManifestRepoItem(
            branch=repo.branch,
            tag=repo.tag,
            # sha1=repo.sha1_full,
            sha1=repo.sha1,
            ignore_submodules=repo.ignore_submodules,
            remotes=repo.remotes,
        )

    def _repos_to_mris(
        self,
        repos: Union[List[Repo], None],
    ) -> None:
        if repos:
            for repo in repos:
                # skip empty Repo(s)
                if repo.branch or repo.tag or repo.sha1:
                    self.mris[repo.dest] = self._repo_to_mri(repo)
                else:
                    ui.warning(f"Skipping empty Repo: {repo.dest}")

    def _status_to_mri(
        self,
        status: Union[Status, Exception],
        w_repo: Repo,
    ) -> ManifestRepoItem:
        if isinstance(status, Status) and status.git.empty is False:
            return ManifestRepoItem(
                branch=status.git.branch,
                tag=status.git.tag,
                sha1=status.git.sha1_full,
                empty=status.git.empty,
                ignore_submodules=w_repo.ignore_submodules,
                remotes=w_repo.remotes,
                groups_considered=True,
            )
        return ManifestRepoItem()

    def _statuses_to_mris(
        self,
        statuses: Union[CollectedStatuses, None],
        w_repos: Union[List[Repo], None],
    ) -> None:
        if statuses and w_repos:
            for repo in w_repos:
                dest = repo.dest
                if isinstance(statuses[dest], Status):
                    self.mris[dest] = self._status_to_mri(statuses[dest], repo)
