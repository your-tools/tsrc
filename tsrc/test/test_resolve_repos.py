from pathlib import Path
from typing import Any, Dict, List, Optional

import ruamel.yaml

from tsrc.cli import resolve_repos
from tsrc.repo import Repo
from tsrc.workspace import Workspace
from tsrc.workspace.config import WorkspaceConfig


def create_manifest(
    tmp_path: Path, *, repos: List[str], groups: Optional[Dict[str, Any]] = None
) -> None:
    config: Dict[str, Any] = {"repos": []}
    if groups:
        config["groups"] = groups
    for name in repos:
        config["repos"].append({"dest": name, "url": f"git@acme.org:{name}"})
    manifest_path = tmp_path / ".tsrc/manifest"
    manifest_path.mkdir(parents=True, exist_ok=True)
    dump_path = manifest_path / "manifest.yml"
    to_write = ruamel.yaml.dump(config)
    assert to_write
    dump_path.write_text(to_write)


def create_workspace(
    tmp_path: Path,
    *,
    repo_groups: Optional[List[str]] = None,
    clone_all_repos: bool = False,
) -> Workspace:
    config = WorkspaceConfig(
        manifest_url="git@acme.org/manifest.git",
        manifest_branch="master",
        shallow_clones=False,
        clone_all_repos=clone_all_repos,
        repo_groups=repo_groups or [],
    )
    config.save_to_file(tmp_path / ".tsrc" / "config.yml")
    return Workspace(tmp_path)


def repo_names(repos: List[Repo]) -> List[str]:
    return [repo.dest for repo in repos]


def test_no_args_no_config_no_default_group(tmp_path: Path) -> None:
    """Scenario:
    * Nothing passed on the command line
    * No default group in the manifest
    * No workspace config

    Should return all repos in the manifest
    """
    create_manifest(tmp_path, repos=["foo", "bar"])
    workspace = create_workspace(tmp_path)
    actual = resolve_repos(workspace, groups=None, all_cloned=False)
    assert repo_names(actual) == ["foo", "bar"]


def test_no_args_no_config_default_group(tmp_path: Path) -> None:
    """Scenario:
    * Nothing passed on the command line
    * A default group in the manifest containing 'foo'
    * A repo named 'outside' in the manifest - not in any group
    * No workspace config

    Should use the default group
    """
    groups = {
        "default": {"repos": ["foo"]},
    }
    create_manifest(tmp_path, repos=["foo", "outside"], groups=groups)
    workspace = create_workspace(tmp_path)

    actual = resolve_repos(workspace, groups=None, all_cloned=False)
    assert repo_names(actual) == ["foo"]


def test_no_args_workspace_configured_with_all_repos(tmp_path: Path) -> None:
    """Scenario:
    * Nothing passed on the command line
    * A default group in the manifest containing foo
    * A repo named 'outside' in the manifest - not in any group
    * Workspace configured with clone_all_repos: True

    Should return everything
    """
    groups = {
        "default": {"repos": ["foo"]},
    }
    create_manifest(tmp_path, repos=["foo", "outside"], groups=groups)
    workspace = create_workspace(tmp_path, clone_all_repos=True)

    actual = resolve_repos(workspace, groups=None, all_cloned=False)
    assert repo_names(actual) == ["foo", "outside"]


def test_no_args_workspace_configured_with_some_groups(tmp_path: Path) -> None:
    """Scenario:
    * Nothing passed on the command line
    * A group named 'group1' in the manifest containing foo
    * A group named 'group2' in the manifest containing bar
    * Workspace configured with repo_groups=[group1]

    Should return foo from group1
    """
    groups = {
        "group1": {"repos": ["foo"]},
        "group2": {"repos": ["bar"]},
    }
    create_manifest(tmp_path, repos=["foo", "bar"], groups=groups)
    workspace = create_workspace(tmp_path, repo_groups=["group1"])

    actual = resolve_repos(workspace, groups=None, all_cloned=False)
    assert repo_names(actual) == ["foo"]


def test_groups_requested(tmp_path: Path) -> None:
    """Scenario:
    * A group named 'group1' in the manifest containing foo
    * A group named 'group2' in the manifest containing bar
    * Workspace configured with repo_groups=[group1, group2]
    * --group group1 used on the command line

    Should return repos from group1
    """
    groups = {
        "group1": {"repos": ["foo"]},
        "group2": {"repos": ["bar"]},
    }
    create_manifest(tmp_path, repos=["foo", "bar"], groups=groups)
    workspace = create_workspace(tmp_path, repo_groups=["group1"])

    actual = resolve_repos(workspace, groups=["group1"], all_cloned=False)
    assert repo_names(actual) == ["foo"]


def test_all_cloned_requested(tmp_path: Path) -> None:
    """Scenario:
    * A group named 'group1' in the manifest containing foo and bar
    * A repo named 'other' in the manifest
    * Workspace configured with repo_groups=[group1]
    * tmp_path / foo and tmp_path / other exists, but not tmp_path / bar
    * --all-cloned used on the command line

    Should return foo and other
    """
    groups = {
        "group1": {"repos": ["foo", "bar"]},
    }
    create_manifest(tmp_path, repos=["foo", "bar", "other"], groups=groups)
    workspace = create_workspace(tmp_path, repo_groups=["group1"])

    (tmp_path / "foo").mkdir(parents=True, exist_ok=True)
    (tmp_path / "other").mkdir(parents=True, exist_ok=True)

    actual = resolve_repos(workspace, groups=None, all_cloned=True)
    assert repo_names(actual) == ["foo", "other"]


def test_filter_inclusive(tmp_path: Path) -> None:
    """Scenario:
    * A group named 'group1' in the manifest containing foo, foo2, bar, bar2
    * A repo named 'other' in the manifest
    * Workspace configured with repo_group=[group]
    * --group group1 used on the command line
    * -r foo used on the command line

    Should return repos foo and foo2 from group1
    """
    groups = {"group1": {"repos": ["foo", "foo2", "bar", "bar2"]}}
    create_manifest(
        tmp_path, repos=["foo", "foo2", "bar", "bar2", "other"], groups=groups
    )
    workspace = create_workspace(tmp_path, repo_groups=["group1"])

    actual = resolve_repos(workspace, groups=["group1"], all_cloned=False, regex="foo")
    assert repo_names(actual) == ["foo", "foo2"]


def test_filter_exclusive(tmp_path: Path) -> None:
    """Scenario:
    * A group named 'group1' in the manifest containing foo, foo2, bar, bar2
    * A repo named 'other' in the manifest
    * Workspace configured with repo_group=[group]
    * --group group1 used on the command line
    * -i foo used on the command line

    Should return repos bar and bar2 from group1
    """
    groups = {"group1": {"repos": ["foo", "foo2", "bar", "bar2"]}}
    create_manifest(
        tmp_path, repos=["foo", "foo2", "bar", "bar2", "other"], groups=groups
    )
    workspace = create_workspace(tmp_path, repo_groups=["group1"])

    actual = resolve_repos(workspace, groups=["group1"], all_cloned=False, iregex="foo")
    assert repo_names(actual) == ["bar", "bar2"]


def test_filter_inclusive_exclusive(tmp_path: Path) -> None:
    """Scenario:
    * A group named 'group1' in the manifest containing foo, foo2, bar, bar2
    * A repo named 'other' in the manifest
    * Workspace configured with repo_group=[group]
    * --group group1 used on the command line
    * -r foo used on the command line
    * -i 2 used on the command line

    Should return repo foo from group1
    """
    groups = {"group1": {"repos": ["foo", "foo2", "bar", "bar2"]}}
    create_manifest(
        tmp_path, repos=["foo", "foo2", "bar", "bar2", "other"], groups=groups
    )
    workspace = create_workspace(tmp_path, repo_groups=["group1"])

    actual = resolve_repos(
        workspace, groups=["group1"], all_cloned=False, regex="foo", iregex="2"
    )
    assert repo_names(actual) == ["foo"]
