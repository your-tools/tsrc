""" Entry point for `tsrc init`. """
import argparse
from pathlib import Path

import cli_ui as ui

from tsrc.cli import (
    add_groups_arg,
    add_num_jobs_arg,
    add_workspace_arg,
    get_num_jobs,
    repos_from_config,
)
from tsrc.errors import Error
from tsrc.local_manifest import LocalManifest
from tsrc.workspace import Workspace
from tsrc.workspace_config import WorkspaceConfig


def configure_parser(subparser: argparse._SubParsersAction) -> None:
    parser = subparser.add_parser("init")
    add_workspace_arg(parser)
    parser.add_argument("manifest_url", help="git url containing the manifest file")
    parser.add_argument(
        "--branch",
        help="use this branch for the manifest",
        dest="manifest_branch",
    )
    parser.add_argument(
        "--shallow",
        action="store_true",
        help="use shallow clones",
        dest="shallow_clones",
    )
    parser.add_argument(
        "-r",
        "--singular-remote",
        help="only use this remote when cloning repositories",
    )

    parser.add_argument(
        "--clone-all-repos",
        action="store_true",
        help="clone all repos from the manifest, regardless of the groups",
    )
    add_groups_arg(parser)
    add_num_jobs_arg(parser)
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> None:
    workspace_path = args.workspace_path or Path.cwd()
    num_jobs = get_num_jobs(args)

    cfg_path = workspace_path / ".tsrc" / "config.yml"

    if cfg_path.exists():
        raise Error(f"Workspace already configured. `{cfg_path}` already exists")

    ui.info_1("Configuring workspace in", ui.bold, workspace_path)

    clone_path = workspace_path / ".tsrc/manifest"
    local_manifest = LocalManifest(clone_path)
    local_manifest.init(url=args.manifest_url, branch=args.manifest_branch)
    manifest_branch = local_manifest.current_branch()

    workspace_config = WorkspaceConfig(
        manifest_url=args.manifest_url,
        manifest_branch=manifest_branch,
        clone_all_repos=args.clone_all_repos,
        repo_groups=args.groups or [],
        shallow_clones=args.shallow_clones,
        singular_remote=args.singular_remote,
    )
    workspace_config.save_to_file(cfg_path)

    workspace = Workspace(workspace_path)
    manifest = workspace.get_manifest()
    workspace.repos = repos_from_config(manifest, workspace_config)
    workspace.clone_missing(num_jobs=num_jobs)
    workspace.set_remotes(num_jobs=num_jobs)
    workspace.perform_filesystem_operations()
    ui.info_2("Workspace initialized")
    ui.info_2("Configuration written in", ui.bold, workspace.cfg_path)
