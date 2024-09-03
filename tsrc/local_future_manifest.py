"""
Local Future Manifest

Obtains information about Future Manifest
by init or update Manifest repository
to *local* directory.

Local Future Manifest will be in:
root_path / ".tsrc" / "future_manifest"

This way we can see how Workspace will transform
after the 'sync'.
"""

from typing import Dict, Tuple, Union

import cli_ui as ui

from tsrc.errors import LoadManifestSchemaError
from tsrc.groups_to_find import GroupsToFind
from tsrc.local_manifest import LocalManifest
from tsrc.manifest import Manifest
from tsrc.manifest_common import ManifestGetRepos
from tsrc.manifest_common_data import ManifestsTypeOfData
from tsrc.repo import Repo
from tsrc.workspace import Workspace


def get_local_future_manifests_manifest_and_repos(
    workspace: Workspace,
    gtf: GroupsToFind,
    must_find_all_groups: bool = False,
    use_same_future_manifest: bool = False,
) -> Tuple[
    Union[Manifest, None], Union[Dict[str, Repo], None], bool, GroupsToFind, bool
]:
    # returns: lfm, lfm_repos, must_find_all_groups, gtf, report_skip_fm_update
    path = workspace.root_path / ".tsrc" / "future_manifest"
    path_to_m_file = path / "manifest.yml"
    report_skip_fm_update: bool = False

    # as Manifest.yml by itself does not have configuration, we need to check
    # Workspace config to apply some missing options
    clone_all_repos = False
    if workspace.config.clone_all_repos is True:
        clone_all_repos = True

    lfm = LocalManifest(path)
    if path.is_dir():
        # if it is already present
        if use_same_future_manifest is False or not path_to_m_file.is_file():
            lfm.update(
                url=workspace.config.manifest_url,
                branch=workspace.config.manifest_branch,
                show_output=False,
                show_cmd=False,
            )
        else:
            report_skip_fm_update = True

    else:
        # first time use
        lfm.init(
            url=workspace.config.manifest_url,
            branch=workspace.config.manifest_branch,
            show_output=False,
            show_cmd=False,
        )

    # read manifest file and obtain raw data
    # lfmm = lfm.get_manifest()
    try:
        lfmm = lfm.get_manifest_safe_mode(ManifestsTypeOfData.FUTURE)
    except LoadManifestSchemaError as lmse:
        ui.warning(lmse)
        return None, None, must_find_all_groups, gtf, False

    mgr = ManifestGetRepos(workspace, lfmm, True, clone_all_repos)

    # get repos that match 'groups'
    repos, must_find_all_groups, gtf = mgr.by_groups(
        gtf, must_find_all_groups=must_find_all_groups
    )

    # repos: make Dict from List
    dict_repos: Dict[str, Repo] = {}
    for repo in repos:
        dict_repos[repo.dest] = repo

    return lfmm, dict_repos, must_find_all_groups, gtf, report_skip_fm_update
