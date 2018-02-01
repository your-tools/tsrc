""" main entry point """

import os

import click
import ui

from tsrc.cli.foreach import main as foreach
from tsrc.cli.init import main as init
from tsrc.cli.log import main as log
from tsrc.cli.push import main as push
from tsrc.cli.status import main as status
from tsrc.cli.sync import main as sync
from tsrc.cli.version import main as version


CONTEXT_SETTINGS = {
    "help_option_names": ['-h', '--help']
}


def setup_ui(*, verbose, quiet):
    actual_verbose = None
    if os.environ.get("VERBOSE"):
        actual_verbose = True
    if verbose:
        actual_verbose = verbose
    ui.setup(verbose=actual_verbose, quiet=quiet)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option("-v", "--verbose", is_flag=True)
@click.option("-q", "--quiet", is_flag=True)
def main(*, verbose, quiet):
    setup_ui(verbose=verbose, quiet=quiet)


main.add_command(foreach)
main.add_command(init)
main.add_command(log)
main.add_command(push)
main.add_command(status)
main.add_command(sync)
main.add_command(version)
