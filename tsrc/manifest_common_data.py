from enum import Enum, unique

import cli_ui as ui


@unique
class ManifestsTypeOfData(Enum):
    LOCAL = 1
    DEEP = 2
    DEEP_BLOCK = 3
    FUTURE = 4


def get_main_color(tod: ManifestsTypeOfData) -> ui.Token:
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
