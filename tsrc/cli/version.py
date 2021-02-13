""" Entry point for tsrc version """

import argparse

import tsrc


def configure_parser(subparser: argparse._SubParsersAction) -> None:
    parser = subparser.add_parser("version")
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> None:
    print("tsrc version", tsrc.__version__)
