import pytest
import ui

import tsrc


class Kaboom(tsrc.Error):
    def __str__(self) -> str:
        return "Kaboom!"


class FakeTask(tsrc.Task[str]):
    def __init__(self) -> None:
        pass

    def on_start(self, *, num_items: int) -> None:
        ui.info("Frobnicating", num_items, "items")

    def display_item(self, item: str) -> str:
        return item

    def process(self, item: str) -> None:
        ui.info("frobnicate", item)
        if item == "bar":
            print("ko :/")
            raise Kaboom()
        ui.info("ok !")


def test_doing_nothing() -> None:
    task = FakeTask()
    tsrc.run_sequence(list(), task)


def test_happy() -> None:
    task = FakeTask()
    tsrc.run_sequence(["foo", "spam"], task)


def test_collect_errors() -> None:
    task = FakeTask()
    with pytest.raises(tsrc.ExecutorFailed):
        tsrc.run_sequence(["foo", "bar"], task)
