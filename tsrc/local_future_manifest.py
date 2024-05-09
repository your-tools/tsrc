"""Local Deep Manifest

If '--deep' is used, checkout Deep Manifest
This is needed only if current Deep Manifest is not checkout-ed to
required branch.

It should checkout Deep Manifest to:
    root_path / ".tsrc" / "future_manifest"
"""

from typing import Dict, Tuple, Union

from tsrc.groups_to_find import GroupsToFind
from tsrc.local_manifest import LocalManifest
from tsrc.manifest import Manifest
from tsrc.manifest_common import ManifestGetRepos
from tsrc.repo import Repo
from tsrc.workspace import Workspace


def get_local_future_manifests_manifest_and_repos(
    workspace: Workspace,
    gtf: GroupsToFind,
    on_manifest_only: bool = False,
    must_find_all_groups: bool = False,
) -> Tuple[Union[Manifest, None], Union[Dict[str, Repo], None], bool, GroupsToFind]:
    path = workspace.root_path / ".tsrc" / "future_manifest"

    clone_all_repos = False
    if workspace.config.clone_all_repos is True:
        clone_all_repos = True

    lfm = LocalManifest(path)
    if path.is_dir():
        lfm.update(
            url=workspace.config.manifest_url,
            branch=workspace.config.manifest_branch,
            show_output=False,
            show_cmd=False,
        )
    else:
        lfm.init(
            url=workspace.config.manifest_url,
            branch=workspace.config.manifest_branch,
            show_output=False,
            show_cmd=False,
        )
    lfmm = lfm.get_manifest()
    mgr = ManifestGetRepos(workspace, lfmm, on_manifest_only, clone_all_repos)
    repos, must_find_all_groups, gtf = mgr.by_groups(
        gtf, must_find_all_groups=must_find_all_groups
    )
    dict_repos: Dict[str, Repo] = {}
    for repo in repos:
        dict_repos[repo.dest] = repo

    return lfmm, dict_repos, must_find_all_groups, gtf
