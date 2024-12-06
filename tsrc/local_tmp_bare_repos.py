"""
# local_tmp_bare_repos

## conditions for use

This is only usefull when these 3 conditions are met:

1st: Reasonable use is only for:
* Deep Manifest
* Future Manifest

2nd: SHA1 must be set for such Repo

3rd: remote must be set and reachable

## What it does:

Bare Git repository should be created
to some temporary location (under '.tsrc')
or updated to required commit SHA1.

current SHA1 is then checked with remote to
count possition ahead/behind.
"""

import hashlib
from pathlib import Path
from typing import List, Optional

from tsrc.cloner import BareCloner

# import cli_ui as ui
from tsrc.errors import LoadManifestSchemaError
from tsrc.executor import process_items
from tsrc.groups_to_find import GroupsToFind
from tsrc.local_manifest import LocalManifest
from tsrc.manifest_common import ManifestGetRepos
from tsrc.manifest_common_data import ManifestsTypeOfData
from tsrc.pcs_repo import PCSRepo
from tsrc.repo import Repo
from tsrc.utils import erase_last_line
from tsrc.workspace import Workspace


def prepare_tmp_bare_dm_repos(
    workspace: Workspace,
    dm: PCSRepo,
    gtf: GroupsToFind,
    num_jobs: int,
) -> List[Repo]:
    """
    Take care of Deep Manifest's Repos to repsect Groups
    """

    # get Repos from Deep Manifest (considering Groups)
    dm_path = workspace.root_path / dm.dest
    ldm = LocalManifest(dm_path)
    try:
        ldmm = ldm.get_manifest_safe_mode(ManifestsTypeOfData.DEEP)
    # except LoadManifestSchemaError as lmse:
    except LoadManifestSchemaError:
        # ui.warning(lmse)
        return []

    # get repos that match Groups provided
    mgr = ManifestGetRepos(workspace, ldmm, True, workspace.config.clone_all_repos)
    repos, _, gtf = mgr.by_groups(gtf, must_find_all_groups=False)

    c_repos: List[Repo] = ready_tmp_bare_repos(
        workspace, ManifestsTypeOfData.DEEP, repos
    )

    return c_repos


def process_bare_repos(
    workspace: Workspace, c_repos: List[Repo], num_jobs: int
) -> List[Repo]:

    # TODO: possibly add 'config' -> 'remote_name=self.config.singular_remote'
    bare_cloner = BareCloner(workspace.root_path)

    process_items(c_repos, bare_cloner, num_jobs=num_jobs)
    erase_last_line()

    return c_repos


def ready_tmp_bare_repos(
    workspace: Workspace, mtod: ManifestsTypeOfData, repos: List[Repo]
) -> List[Repo]:

    # create parent directory if it does not exists
    if repos:
        mtod_path: str
        if mtod == ManifestsTypeOfData.DEEP:
            mtod_path = ".tmp_dm_repos"
        elif mtod == ManifestsTypeOfData.FUTURE:
            mtod_path = ".tmp_fm_repos"
        else:
            return []  # do not continue

        tmp_dir = workspace.root_path / ".tsrc" / mtod_path
        if not tmp_dir.is_dir():
            tmp_dir.mkdir(parents=True, exist_ok=True)

    # create Repo's directory if it does not exists when there is SHA1
    c_repos: List[Repo] = []  # consider repos (to get the possition)
    for repo in repos:
        if repo.sha1 and repo.remotes:
            h = hashlib.sha1(repo.clone_url.encode())
            # create dirname with hash of URL
            this_dir = h.hexdigest()[:13] + "_" + repo.dest
            repo_dir = tmp_dir / this_dir

            # check if there is Repo in Workspace
            possible_w_path = workspace.root_path / repo.dest
            possible_w_path_git = possible_w_path / ".git"
            bare_clone_path: Optional[Path] = None
            if possible_w_path_git.is_dir():
                bare_clone_path = possible_w_path

            # add Repo that can be processed by 'process_items'
            c_repos.append(
                Repo(
                    dest=str(repo_dir),
                    remotes=repo.remotes,
                    branch=repo.branch,
                    keep_branch=repo.keep_branch,
                    is_default_branch=repo.is_default_branch,
                    orig_branch=repo.orig_branch,
                    sha1=repo.sha1,
                    tag=repo.tag,
                    shallow=False,
                    is_bare=True,
                    _bare_clone_path=bare_clone_path,
                    _bare_clone_mtod=mtod,
                    _bare_clone_orig_dest=repo.dest,
                    _bare_clone_is_ok=repo._bare_clone_is_ok,
                )
            )

    return c_repos
