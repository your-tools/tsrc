import cli_ui as ui
import pytest

from tsrc.errors import Error
from tsrc.executor import ExecutorFailed, Task, run_sequence


class Kaboom(Error):
    def __str__(self) -> str:
        return "Kaboom!"


class FakeTask(Task[str]):
    def __init__(self) -> None:
        pass

    def on_start(self, *, num_items: int) -> None:
        ui.info("Frobnicating", num_items, "items")

    def display_item(self, item: str) -> str:
        return item

    def process(self, index: int, count: int, item: str) -> None:
        ui.info_count(index, count, "frobnicate", item)
        if item == "bar":
            print("ko :/")
            raise Kaboom()
        ui.info("ok !")


def test_doing_nothing() -> None:
    task = FakeTask()
    run_sequence([], task)


def test_happy() -> None:
    task = FakeTask()
    run_sequence(["foo", "spam"], task)


def test_collect_errors() -> None:
    task = FakeTask()
    with pytest.raises(ExecutorFailed):
        run_sequence(["foo", "bar"], task)
