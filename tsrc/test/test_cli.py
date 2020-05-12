from typing import Any, Dict, List, Optional
import argparse

from tsrc.repo import Repo
from tsrc.manifest import Manifest
from tsrc.workspace.config import WorkspaceConfig
from tsrc.cli import resolve_repos


def new_manifest(
    *, repos: List[str], groups: Optional[Dict[str, Any]] = None
) -> Manifest:
    config: Dict[str, Any] = {"repos": []}
    if groups:
        config["groups"] = groups
    for name in repos:
        config["repos"].append({"src": name, "url": f"git@acme.org:{name}"})
    res = Manifest()
    res.apply_config(config)
    return res


def new_workspace_config(
    *, repo_groups: Optional[List[str]] = None, clone_all_repos: bool = False
) -> WorkspaceConfig:
    return WorkspaceConfig(
        manifest_url="git@acme.org/manifest.git",
        manifest_branch="master",
        shallow_clones=False,
        clone_all_repos=clone_all_repos,
        repo_groups=repo_groups or [],
    )


def new_args(
    *, all_repos: bool = False, groups: Optional[List[str]] = None
) -> argparse.Namespace:
    return argparse.Namespace(all_repos=all_repos, groups=groups)


def repo_names(repos: List[Repo]) -> List[str]:
    return [repo.src for repo in repos]


class TestResolveRepo:
    @staticmethod
    def test_no_args_no_config_no_default_group() -> None:
        """ Scenario:
        * Nothing passed on the command line
        * No default group in the manifest
        * No workspace config

        => Should return all repos in the manifest
        """
        manifest = new_manifest(repos=["foo", "bar"])
        workspace_config = new_workspace_config()
        args = new_args()

        actual = resolve_repos(manifest, args=args, workspace_config=workspace_config)
        assert repo_names(actual) == ["foo", "bar"]

    @staticmethod
    def test_no_args_no_config_default_group() -> None:
        """ Scenario:
        * Nothing passed on the command line
        * A default group in the manifest containing 'foo'
        * A repo named 'outside' in the manifest - not in any group
        * No workspace config

        => Should use the default group
        """
        groups = {
            "default": {"repos": ["foo"]},
        }
        manifest = new_manifest(repos=["foo", "outside"], groups=groups)
        workspace_config = new_workspace_config()
        args = new_args()

        actual = resolve_repos(manifest, args=args, workspace_config=workspace_config)
        assert repo_names(actual) == ["foo"]

    @staticmethod
    def test_no_args_workspace_configured_with_all_repos() -> None:
        """ Scenario:
        * Nothing passed on the command line
        * A default group in the manifest containing foo
        * A repo named 'outside' in the manifest - not in any group
        * Workspace configured with clone_all_repos: True

        => Should return everything
        """
        groups = {
            "default": {"repos": ["foo"]},
        }
        manifest = new_manifest(repos=["foo", "outside"], groups=groups)
        workspace_config = new_workspace_config(clone_all_repos=True)
        args = new_args()

        actual = resolve_repos(manifest, args=args, workspace_config=workspace_config)
        assert repo_names(actual) == ["foo", "outside"]

    @staticmethod
    def test_no_args_workspace_configured_with_some_groups() -> None:
        """ Scenario:
        * Nothing passed on the command line
        * A group named 'group1' in the manifest containing foo
        * A group named 'group2' in the manifest containing bar
        * Workspace configured with repo_groups=[group1]

        => Should return foo from group1
        """
        groups = {
            "group1": {"repos": ["foo"]},
            "group2": {"repos": ["bar"]},
        }
        manifest = new_manifest(repos=["foo", "bar"], groups=groups)
        workspace_config = new_workspace_config(repo_groups=["group1"])
        args = new_args()

        actual = resolve_repos(manifest, args=args, workspace_config=workspace_config)
        assert repo_names(actual) == ["foo"]

    @staticmethod
    def test_all_repos_requested() -> None:
        """ Scenario:
        * A group named 'group1' in the manifest containing foo
        * A group named 'group2' in the manifest containing bar
        * Workspace configured with repo_groups=[group1]

        => Should return everything
        """
        groups = {
            "group1": {"repos": ["foo"]},
            "group2": {"repos": ["bar"]},
        }
        manifest = new_manifest(repos=["foo", "bar"], groups=groups)
        workspace_config = new_workspace_config(repo_groups=["group1"])
        args = new_args(all_repos=True)

        actual = resolve_repos(manifest, args=args, workspace_config=workspace_config)
        assert repo_names(actual) == ["foo", "bar"]

    @staticmethod
    def test_groups_requested() -> None:
        """ Scenario:
        * A group named 'group1' in the manifest containing foo
        * A group named 'group2' in the manifest containing bar
        * Workspace configured with repo_groups=[group1, group2]
        * --group group1 used on the command line

        => Should return repos from group1
        """
        groups = {
            "group1": {"repos": ["foo"]},
            "group2": {"repos": ["bar"]},
        }
        manifest = new_manifest(repos=["foo", "bar"], groups=groups)
        workspace_config = new_workspace_config(repo_groups=["group1"])
        args = new_args(groups=["group1"])

        actual = resolve_repos(manifest, args=args, workspace_config=workspace_config)
        assert repo_names(actual) == ["foo"]
