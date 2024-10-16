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


def mtod_can_ignore_remotes() -> List[ManifestsTypeOfData]:
    rl: List[ManifestsTypeOfData] = [
        ManifestsTypeOfData.DEEP,
        ManifestsTypeOfData.DEEP_ON_UPDATE,
        ManifestsTypeOfData.DEEP_BLOCK,
        ManifestsTypeOfData.FUTURE,
    ]
    return rl


def get_main_color(tod: ManifestsTypeOfData) -> ui.Token:
    # TODO: rename with prefix 'mtod'
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
    return ui.reset
