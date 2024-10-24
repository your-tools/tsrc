from enum import Enum, unique
from typing import List

import cli_ui as ui


@unique
class ManifestsTypeOfData(Enum):
    LOCAL = 1
    DEEP = 2
    DEEP_ON_UPDATE = 3  # do not put warning about missing element
    DEEP_BLOCK = 4
    FUTURE = 5
    SAVED = 6  # manifest created by '--save-to'


def get_mtod_str(tod: ManifestsTypeOfData) -> str:
    if tod == ManifestsTypeOfData.LOCAL:
        return "Local Manifest"
    if tod == ManifestsTypeOfData.DEEP:
        return "Deep Manifest"
    if tod == ManifestsTypeOfData.DEEP_ON_UPDATE:
        return "Deep Manifest on UPDATE"
    if tod == ManifestsTypeOfData.DEEP_BLOCK:
        return "Deep Manifest's block"
    if tod == ManifestsTypeOfData.FUTURE:
        return "Future Manifest"
    if tod == ManifestsTypeOfData.SAVED:
        return "Saved Manifest"


def mtod_can_ignore_remotes() -> List[ManifestsTypeOfData]:
    rl: List[ManifestsTypeOfData] = [
        # only for LOCAL Manifest the missing remote
        # cannot be ignored.
        ManifestsTypeOfData.DEEP,
        ManifestsTypeOfData.DEEP_ON_UPDATE,
        ManifestsTypeOfData.DEEP_BLOCK,
        ManifestsTypeOfData.FUTURE,
        ManifestsTypeOfData.SAVED,
    ]
    return rl


def mtod_get_main_color(tod: ManifestsTypeOfData) -> ui.Token:
    # for Local Manifest (using for Manifest's Marker color)
    if tod == ManifestsTypeOfData.LOCAL:
        return ui.reset

    # for Deep Manifest (for: 'dest' color, MM color)
    if tod == ManifestsTypeOfData.DEEP:
        return ui.purple

    # for Deep Manifest block (for: square brackets color)
    if tod == ManifestsTypeOfData.DEEP_BLOCK:
        return ui.brown

    # for Future Manifest (for 'dest' color, MM color)
    if tod == ManifestsTypeOfData.FUTURE:
        return ui.cyan

    return ui.reset  # we should never reach it
