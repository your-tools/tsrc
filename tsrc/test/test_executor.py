import pytest
import ui

import tsrc
import tsrc.executor


class Kaboom(tsrc.Error):
    def __str__(self):
        return "Kaboom!"


class FakeTask(tsrc.executor.Task):
    def __init__(self):
        pass

    def description(self):
        print("Frobnicating all items")

    def display_item(self, item):
        return item

    def process(self, item):
        ui.info("frobnicate", item)
        if item == "bar":
            print("ko :/")
            raise Kaboom()
        ui.info("ok !")


def test_doing_nothing():
    task = FakeTask()
    tsrc.executor.run_sequence(list(), task)


def test_happy():
    task = FakeTask()
    tsrc.executor.run_sequence(["foo", "spam"], task)


def test_collect_errors():
    task = FakeTask()
    with pytest.raises(tsrc.executor.ExecutorFailed):
        tsrc.executor.run_sequence(["foo", "bar"], task)
