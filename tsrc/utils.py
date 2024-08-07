import shutil
from typing import List

import cli_ui as ui


def erase_last_line() -> None:
    terminal_size = shutil.get_terminal_size()
    ui.info(" " * terminal_size.columns, end="\r")


def len_of_cli_ui(ui_tokens: List[ui.Token]) -> int:
    len_: int = 0
    for i in ui_tokens:
        if isinstance(i, str):
            len_ += len(i) + 1

    if len_ > 0:
        len_ -= 1
    return len_


def align_left(l_just: int, l_str: str) -> List[ui.Token]:
    str_: str = ""
    if l_just == 1:
        str_ = " "
    if l_just > 1:
        str_ = " ".ljust(l_just)
    return [str_ + l_str]
