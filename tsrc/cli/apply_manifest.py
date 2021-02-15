""" Entry point for `tsrc apply-manifest`. """

import argparse
from pathlib import Path

import tsrc.manifest
from tsrc.cli import add_workspace_arg, get_workspace, repos_from_config


def configure_parser(subparser: argparse._SubParsersAction) -> None:
    parser = subparser.add_parser("apply-manifest")
    parser.add_argument("manifest_path", help="path to the local manifest", type=Path)
    add_workspace_arg(parser)
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> None:
    manifest = tsrc.manifest.load(args.manifest_path)
    workspace = get_workspace(args)
    workspace.repos = repos_from_config(manifest, workspace.config)
    workspace.clone_missing()
    workspace.set_remotes()
    workspace.perform_filesystem_operations()
