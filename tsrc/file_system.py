import os

import cli_ui as ui
from path import Path

import tsrc


def safe_link(*, source: Path, target: Path) -> None:
    """ Safely create a link in 'source' pointing to 'target' """
    # Not: we need to call both islink() and exist() to safely ensure
    # that the link exists:
    #
    #    islink()  exists()    Description
    #    ----------------------------------------------------------
    #    False     False       source doesn't currently exist : OK
    #    False     True        source corresponds to a file or dir : Error!
    #    True      False       broken symlink, need to remove
    #    True      True        symlink points to a valid target, check target
    #    ----------------------------------------------------------
    make_link = check_link(source=source, target=target)
    if make_link:
        ui.info_3("Creating link", source, "->", target)
        os.symlink(
            target.normpath(), source.normpath(), target_is_directory=target.isdir()
        )


def check_link(*, source: Path, target: Path) -> bool:
    remove_link = False
    if source.exists() and not source.islink():
        raise tsrc.Error("Specified symlink source exists but is not a link")
        return False
    if source.islink():
        if source.exists():
            # symlink exists and points to some target
            current_target = source.readlink()
            if current_target.realpath() == target.realpath():
                ui.info_3("Leaving existing link")
                return False
            else:
                ui.info_3("Replacing existing link")
                remove_link = True
        else:
            # symlink exists, but points to a non-existent target
            ui.info_3("Replacing broken link")
            remove_link = True
    if remove_link:
        os.unlink(source)
    return True
