from typing import List

import cli_ui as ui

from tsrc.errors import Error
from tsrc.executor import (
    Outcome,
    Task,
    process_items,
    process_items_parallel,
    process_items_sequence,
)


class Kaboom(Error):
    def __init__(self) -> None:
        self.message = "Kaboom"


class FakeTask(Task[str]):
    """This is a fake Task that can be used for testing.

    Note that it will raise an instance of the Kaboom exception
    when processing an item whose value is "failing"

    """

    def __init__(self) -> None:
        pass

    def describe_process_start(self, item: str) -> List[ui.Token]:
        return ["Frobnicating", item]

    def describe_process_end(self, item: str) -> List[ui.Token]:
        return [item, "ok"]

    def process(self, index: int, count: int, item: str) -> Outcome:
        if item == "failing":
            raise Kaboom()
        return Outcome.empty()

    def describe_item(self, item: str) -> str:
        return item


def test_sequence_nothing() -> None:
    task = FakeTask()
    items: List[str] = []
    actual = process_items_sequence(items, task)
    assert not actual


def test_sequence_happy() -> None:
    task = FakeTask()
    actual = process_items_sequence(["foo", "bar"], task)
    assert not actual["foo"].error
    assert not actual["bar"].error


def test_sequence_sad() -> None:
    task = FakeTask()
    actual = process_items(["foo", "failing", "bar"], task)
    assert actual.errors["failing"].message == "Kaboom"


def test_parallel_nothing() -> None:
    task = FakeTask()
    items: List[str] = []
    actual = process_items_parallel(items, task, num_jobs=2)
    assert not actual


def test_parallel_happy() -> None:
    task = FakeTask()
    ui.info("Frobnicating 4 items with two workers")
    actual = process_items_parallel(["foo", "bar", "baz", "quux"], task, num_jobs=2)
    ui.info("Done")
    for outcome in actual.values():
        assert outcome.success()


def test_parallel_sad() -> None:
    task = FakeTask()
    actual = process_items(["foo", "bar", "failing", "baz", "quux"], task, num_jobs=2)
    errors = actual.errors
    assert errors["failing"].message == "Kaboom"
