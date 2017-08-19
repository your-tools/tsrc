from tsrc import ui
import tsrc
import tsrc.executor

import pytest


class Kaboom(tsrc.Error):
    def __str__(self):
        return "Kaboom!"


class FakeActor(tsrc.executor.Actor):
    def __init__(self):
        pass

    def process(self, item):
        ui.info("frobnicate", item)
        if item == "bar":
            print("ko :/")
            raise Kaboom()
        ui.info("ok !")


def test_doing_nothing():
    actor = FakeActor()
    tsrc.executor.run_sequence(list(), actor)


def test_happy():
    actor = FakeActor()
    tsrc.executor.run_sequence(["foo", "spam"], actor)


def test_collect_errors():
    actor = FakeActor()
    with pytest.raises(tsrc.executor.ExecutorFailed):
        tsrc.executor.run_sequence(["foo", "bar"], actor)
