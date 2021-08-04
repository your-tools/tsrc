import cli_ui as ui
import pytest

from tsrc.errors import Error
from tsrc.executor import ExecutorFailed, Task, run_sequence


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

    def on_failure(self, *, num_errors: int) -> None:
        ui.error("Failed to frobnicate some items")

    def display_item(self, item: str) -> str:
        return item

    def process(self, index: int, count: int, item: str) -> None:
        ui.info_count(index, count, "frobnicate", item)
        if item == "failing":
            print("ko :/")
            raise Kaboom()
        ui.info("ok !")


def test_doing_nothing() -> None:
    task = FakeTask()
    run_sequence([], task)


def test_happy() -> None:
    task = FakeTask()
    run_sequence(["foo", "bar"], task)


def test_collect_errors() -> None:
    task = FakeTask()
    with pytest.raises(ExecutorFailed):
        run_sequence(["foo", "failing", "bar"], task)
