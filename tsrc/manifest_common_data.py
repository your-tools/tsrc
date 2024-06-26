from enum import Enum, unique

import cli_ui as ui


@unique
class ManifestsTypeOfData(Enum):
    LOCAL = 1
    DEEP = 2
    FUTURE = 3


def get_main_color(tod: ManifestsTypeOfData) -> ui.Token:
    if tod == ManifestsTypeOfData.LOCAL:
        return ui.reset
    if tod == ManifestsTypeOfData.DEEP:
        return ui.purple
    if tod == ManifestsTypeOfData.FUTURE:
        return ui.cyan
    return ui.reset
