""" Custom exceptions """

from pathlib import Path
from typing import Any

DOC_URL = "https://dmerejkowsky.github.io/tsrc"


class Error(Exception):
    """Base class for our own errors."""

    def __init__(self, *args: Any) -> None:
        super().__init__(self, *args)
        self.message = " ".join(str(x) for x in args)

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


class InvalidConfig(Error):
    def __init__(self, config_path: Path, cause: Exception) -> None:
        self.config_path = config_path
        self.cause = cause
        super().__init__(self.detailed_message)

    @property
    def detailed_message(self) -> str:
        res = f"{self.config_path}: {self.cause}"
        res += "\n"
        res += f"See {DOC_URL} for details"
        return res

    def __str__(self) -> str:
        return self.detailed_message


class MissingRepo(Error):
    def __init__(self, dest: str):
        super().__init__(f"No repo found in '{dest}'. Please run `tsrc sync`")
