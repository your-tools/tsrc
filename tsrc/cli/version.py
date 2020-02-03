""" Entry point for tsrc version """

import argparse
import tsrc


def main(args: argparse.Namespace) -> None:
    print("tsrc version", tsrc.__version__)
