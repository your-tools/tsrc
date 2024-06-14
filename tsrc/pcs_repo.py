"""Pseudo Current Static Repo.

'pseudo' as it is not full-fledged Repository
'current' as it only get current data at the moment,
'static' as once object is initialized, it cannot be changed
'repo' as it has repo-like features

This class is only for data transfer.
The reason behind is not to pass many variables
into the function, but one.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

from tsrc.git_remote import remote_urls_are_same
from tsrc.groups_to_find import GroupsToFind
from tsrc.manifest_common import ManifestGetRepos
from tsrc.repo import Remote, Repo
from tsrc.status_endpoint import Status
from tsrc.workspace import Workspace


@dataclass(frozen=True)
class PCSRepo:
    dest: str
    branch: Union[str, None]
    url: Optional[str] = None
    _origin = "origin"

    def get_origin(self) -> str:
        return type(self)._origin

    origin = property(get_origin)


def repo_from_pcsrepo(
    st_m: PCSRepo,
) -> Union[Repo, None]:
    if st_m.url and st_m.branch:
        origin = Remote(st_m.origin, st_m.url)
        remotes = []
        remotes.append(origin)
        return Repo(
            dest=st_m.dest,
            remotes=remotes,
            branch=st_m.branch,
        )
    return None


StatusOrError = Union[Status, Exception]


def get_deep_manifest_from_local_manifest_pcsrepo(
    # manifest: Manifest,
    workspace: Workspace,
    # groups: Union[List[str], None],
    gtf: GroupsToFind,
) -> Tuple[Union[PCSRepo, None], GroupsToFind]:
    """
    Returns:
    * 1st: PCSRepo of Deep Manifest (if found)
    * 2nd: GroupsToFind: updated for future use
    """
    manifest = workspace.local_manifest.get_manifest()
    mgr = ManifestGetRepos(workspace, manifest, workspace.config.clone_all_repos)
    all_repos, _, new_gtf = mgr.by_groups(gtf)
    _, pcs_repo = get_deep_manifest_pcsrepo(all_repos, workspace.config.manifest_url)

    return pcs_repo, new_gtf


def get_deep_manifest_pcsrepo(
    all_repos: List[Repo],
    m_url: str,
) -> Tuple[List[Repo], Union[PCSRepo, None]]:
    """Gets Deep Manifest properly.
    If you call this function from 'status', than
    you can ignore 1st returned value and just use the 2nd one"""
    repos = []
    for repo in all_repos:
        repo_remotes = repo.remotes
        is_found = False
        for remote in repo_remotes:
            if remote.url and remote_urls_are_same(remote.url, m_url) is True:
                is_found = True
                break
        if is_found is True:
            repos += [repo]
            break
    dm = None
    if repos:
        dm = PCSRepo(repos[0].dest, repos[0].branch, url=m_url)
    return repos, dm


"""here 'url' is provided directly
search through statuses:
(ManifestStatus (as '.manifest)) ->
(Repo (as '.repo))"""


def get_workspace_manifest_pcsrepo(
    statuses: Dict[str, StatusOrError],
    m_url: str,
) -> Union[PCSRepo, None]:
    for dest, status in statuses.items():
        if isinstance(status, Status):
            for remote in status.manifest.repo.remotes:
                if remote_urls_are_same(remote.url, m_url) is True:
                    branch = None
                    if isinstance(status.git.branch, str):
                        branch = status.git.branch
                    return PCSRepo(dest=dest, branch=branch, url=m_url)
    return None


"""here the 'url' is taken from 'workspace'
search through Repos to find Manifest Repo"""


# TODO: move this to ManifestTools in some time
def is_manifest_in_workspace(
    workspace: Workspace,
    repos: List[Repo],
) -> Union[PCSRepo, None]:
    for x in repos:
        this_dest = x.dest
        this_branch = x.branch
        for y in x.remotes:
            if (
                y.url
                and remote_urls_are_same(  # noqa: W503
                    y.url, workspace.config.manifest_url
                )
                is True
            ):
                # go with 1st one found
                return PCSRepo(
                    this_dest, this_branch, url=workspace.config.manifest_url
                )
    return None
