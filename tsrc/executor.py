""" Helpers to run things on multiple repos and collect errors """

import abc
import sys
from typing import Any, Generic, List, Tuple, TypeVar  # noqa

import cli_ui as ui

import tsrc


T = TypeVar("T")


class ExecutorFailed(tsrc.Error):
    pass


class Task(Generic[T], metaclass=abc.ABCMeta):
    def on_start(self, *, num_items: int) -> None:
        pass

    def on_failure(self, *, num_errors: int) -> None:
        pass

    def on_success(self) -> None:
        pass

    @abc.abstractmethod
    def display_item(self, item: T) -> str:
        pass

    @abc.abstractmethod
    def process(self, index: int, count: int, item: T) -> None:
        pass


class SequentialExecutor(Generic[T]):
    def __init__(self, task: Task[T]) -> None:
        self.task = task
        self.errors = []  # type: List[Tuple[T, tsrc.Error]]

    def process(self, items: List[T]) -> None:
        self.task.on_start(num_items=len(items))

        self.errors = []
        num_items = len(items)
        for i, item in enumerate(items):
            self.process_one(i, num_items, item)

        if self.errors:
            self.handle_errors()
        else:
            self.task.on_success()

    def handle_errors(self) -> None:
        self.task.on_failure(num_errors=len(self.errors))
        for item, error in self.errors:
            item_desc = self.task.display_item(item)
            message = [ui.green, "*", " ", ui.reset, ui.bold, item_desc]
            if error.message:
                message.extend([ui.reset, ": ", error.message])
            ui.info(*message, sep="", fileobj=sys.stderr)
        raise ExecutorFailed()

    def process_one(self, index: int, count: int, item: T) -> None:
        try:
            self.task.process(index, count, item)
        except tsrc.Error as error:
            self.errors.append((item, error))


def run_sequence(items: List[T], task: Task[Any]) -> None:
    executor = SequentialExecutor(task)
    return executor.process(items)
