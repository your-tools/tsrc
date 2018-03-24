""" Helpers to run things on multiple repos and collect errors """

import abc
from typing import List, Tuple, Any

import ui

import tsrc


class ExecutorFailed(tsrc.Error):
    pass


class Task(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def description(self) -> str:
        pass

    # pylint: disable=no-self-use
    def quiet(self) -> bool:
        return False

    @abc.abstractmethod
    def display_item(self, _) -> str:
        pass

    @abc.abstractmethod
    def process(self, _) -> None:
        pass


class SequentialExecutor():
    def __init__(self, task: Task) -> None:
        self.task = task
        self.errors: List[Tuple[Any, tsrc.Error]] = list()

    def process(self, items: List[Any]) -> None:
        if not items:
            return
        ui.info_1(self.task.description())

        self.errors = list()
        num_items = len(items)
        for i, item in enumerate(items):
            if not self.task.quiet():
                ui.info_count(i, num_items, end="")
            self.process_one(item)

        if self.errors:
            self.handle_errors()

    def handle_errors(self) -> None:
        ui.error(self.task.description(), "failed")
        for item, error in self.errors:
            item_desc = self.task.display_item(item)
            message = [ui.green, "*", " ", ui.reset, ui.bold, item_desc]
            if error.message:
                message.extend([ui.reset, ": ", error.message])
            ui.info(*message, sep="")
        raise ExecutorFailed()

    def process_one(self, item) -> None:
        try:
            self.task.process(item)
        except tsrc.Error as error:
            self.errors.append((item, error))


def run_sequence(items: List[Any], task: Task) -> None:
    executor = SequentialExecutor(task)
    return executor.process(items)
