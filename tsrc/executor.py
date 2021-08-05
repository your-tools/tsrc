""" Helpers to run the same task on multiple items and collect errors.

"""

import abc
import concurrent
import sys
from concurrent.futures import ThreadPoolExecutor

from typing import Any, Generic, List, Tuple, TypeVar  # noqa

import cli_ui as ui

import tsrc

T = TypeVar("T")


class ExecutorFailed(tsrc.Error):
    pass


class Task(Generic[T], metaclass=abc.ABCMeta):
    """Represent an action to be performed."""

    @abc.abstractmethod
    def process(self, index: int, count: int, item: T) -> int:
        """
        Daughter classes should override this method to provide the code
        that processes the item.

        It returns the item's index (for printing out its output in a synchronized
        if the item was processes paralleled).
        """
        pass

    def on_start(self, *, num_items: int) -> None:
        """Called when the executor starts."""
        pass

    def on_failure(self, *, num_errors: int) -> None:
        """Called when the executor ends and `num_errors` is not 0."""
        pass

    def on_success(self) -> None:
        """Called when the task succeeds on all items."""
        pass

    @abc.abstractmethod
    def display_item(self, item: T) -> str:
        """Called to describe the item that caused an error."""
        pass


class SequentialExecutor(Generic[T]):
    """Run the task on all items one at a time, while collecting errors that
    occur in the process.
    """

    def __init__(self, task: Task[T]) -> None:
        self.task = task
        # Collected errors as a list tuples: (item, caught_exception)
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


class ParallelExecutor(SequentialExecutor):
    """Run the tasks using `n` threads, while collecting errors that
    occur in the process.
    """

    def __init__(self, task: Task[T], max_workers: int) -> None:
        super().__init__(task)
        self.max_workers = max_workers

    def process(self, items: List[T]) -> None:
        self.task.on_start(num_items=len(items))
        self.errors = []
        num_items = len(items)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []

            for i, item in enumerate(items):
                futures.append(executor.submit(self.task.process, i, num_items, item))

            for future in concurrent.futures.as_completed(futures):
                try:
                    buffer_id = future.result()
                    ui.print_buffer(buffer_id)
                except tsrc.Error as error:
                    self.errors.append((item, error))

        if self.errors:
            self.handle_errors()
        else:
            self.task.on_success()


def run_sequence(items: List[T], task: Task[Any]) -> None:
    # executor = SequentialExecutor(task)
    executor = ParallelExecutor(task, 10)
    return executor.process(items)
