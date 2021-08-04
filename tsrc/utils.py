import shutil

import cli_ui as ui


def erase_last_line() -> None:
    terminal_size = shutil.get_terminal_size()
    ui.info(" " * terminal_size.columns, end="\r")
