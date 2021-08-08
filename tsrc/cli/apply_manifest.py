""" Entry point for `tsrc apply-manifest`. """

import argparse
from pathlib import Path

from tsrc.cli import (
    add_num_jobs_arg,
    add_workspace_arg,
    get_num_jobs,
    get_workspace,
    repos_from_config,
)
from tsrc.manifest import load_manifest


def configure_parser(subparser: argparse._SubParsersAction) -> None:
    parser = subparser.add_parser("apply-manifest")
    parser.add_argument("manifest_path", help="path to the local manifest", type=Path)
    add_workspace_arg(parser)
    add_num_jobs_arg(parser)
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.manifest_path)
    num_jobs = get_num_jobs(args)
    workspace = get_workspace(args)
    workspace.repos = repos_from_config(manifest, workspace.config)
    workspace.clone_missing(num_jobs=num_jobs)
    workspace.set_remotes(num_jobs=num_jobs)
    workspace.perform_filesystem_operations(manifest=manifest)
