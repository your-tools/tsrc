""" Helpers to:
  * run the same task on multiple items
  * collect errors
  * display a summary of what happened at the end


This module is used by most of `tsrc` actions, which almost
always run some piece of code for each repository in the workspace.

The entry point in the `process_items()` function, which is explained
it detail below.

# The process_items() function

Here's what happens when you call process_items(items, task), where
items is a list of "T" and task an instance which implements
the Task[T] interface

## Running tasks

* If num_jobs is None, the SequentialExecutor is used,
  otherwise the ParallelExecutor is used. The  `parallel` boolean
  attribute on the Task instances is set accordingly.
* Both the SequentialExecutor and the ParallelExecutor will call
  Task.process() for each item, but the SequentialExecutor will do
  it in a simple loop, and ParallelExecutor will use a ThreadPoolExecutor

## Displaying output when the tasks at running

We want to keep the output of tsrc clean, while still providing
sufficient information to the user.

To that end, we use the describe_process_start() and describe_process_end()
during the parallel execution, which gives an output like this:

    (1/3) Frobnicating foo (when the process for for foo starts)

or:
    (2/3) bar ok (when the process for 'bar' ends)

Note that describe_process_start and describe_process_end are *not* used
when using the SequentialExecutor

The rationale is that when you use the SequentialExecutor, you can display
much more information to the user *as it happens*.

For instance, when calling `git fetch` with the SequentialExecutor, it's
useful to call `run_git` without capturing output so that the progress of
`git fetch` is clearly visible. On the other hand, displaying the progress
of `git fetch` when several repos are being synced at the same time would
only be confusing.

That's why the Task implementations use `self.info_*` and `self.run_git`
which will produce the correct behavior depending on the `self.parallel`
attribute.

## Displaying output after all items are processed

Sometimes we want to provide the user with a summary of what
happens. For instance, when using `tsrc sync`, you may want to know
which repositories have been updated, or for which repositories
an error occurred, but you don't really care about repositories
which were already up to date.

To that end, the process_item() of each Task instance returns an Outcome
class, which may contain an error message, or a summary.

Back to our `tsrc sync` example, the `Syncer` task will put the output
of the `git merge` command in the summary when `parallel` is True,
and keep it empty when `parallel` is False, because the user already
saw the git output when processing items sequentially.

Finally, the summary may contain an `error` instance, either set by the
Task itself, or set by the Executor when an exception occurred.

## Processing collected outcomes

As explained above, each invocation of Task.process_item produces an Outcome
instance.

The process_items() section builds an OutcomeCollection which can be used
to print the summary, or an error message when relevant.

"""

import abc
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Generic, List, Optional, TypeVar

import attr
import cli_ui as ui

from tsrc.errors import Error
from tsrc.git import run_git
from tsrc.utils import erase_last_line

T = TypeVar("T")


class ExecutorFailed(Error):
    pass


@attr.s
class Outcome:
    """The result of processing an item."""

    error: Optional[Error] = attr.ib()
    summary: Optional[str] = attr.ib()

    @classmethod
    def empty(cls) -> "Outcome":
        return cls(error=None, summary=None)

    @classmethod
    def from_error(cls, error: Error) -> "Outcome":
        return cls(error=error, summary=None)

    @classmethod
    def from_summary(cls, message: str) -> "Outcome":
        return cls(error=None, summary=message)

    @classmethod
    def from_lines(cls, lines: List[str]) -> "Outcome":
        if lines:
            message = "\n".join(lines)
            return cls(error=None, summary=message)
        else:
            return cls.empty()

    def success(self) -> bool:
        return self.error is None


class OutcomeCollection:
    """Collect several Outcome instances"""

    def __init__(self, outcomes: Dict[str, Outcome]) -> None:
        self.summary = []
        self.errors = {}
        for item, outcome in outcomes.items():
            if outcome.summary:
                self.summary.append(outcome.summary)
            if outcome.error:
                self.errors[item] = outcome.error

    def print_summary(self) -> None:
        if not self.summary:
            return
        for summary in self.summary:
            ui.info(summary)

    def print_errors(self) -> None:
        for (item, error) in self.errors.items():
            ui.info(ui.red, "*", ui.reset, item, ":", error)


class Task(Generic[T], metaclass=abc.ABCMeta):
    """Represent an action to be performed."""

    def __init__(self, *, parallel: bool):
        self.parallel = parallel

    def info(self, *args: Any, **kwargs: Any) -> None:
        """Same as cli_ui.info(), except this is a no-op if the
        task is run in parallel with other tasks.

        """
        if not self.parallel:
            ui.info(*args, **kwargs)

    def info_2(self, *args: Any, **kwargs: Any) -> None:
        """Same as cli_ui.info_2(), except this is a no-op if the
        task is run in parallel with other tasks.

        """
        if not self.parallel:
            ui.info_2(*args, **kwargs)

    def info_3(self, *args: Any, **kwargs: Any) -> None:
        """Same as cli_ui.info_3(), except this is a no-op if the
        task is run in parallel with other tasks.

        """
        if not self.parallel:
            ui.info_3(*args, **kwargs)

    def info_count(self, index: int, count: int, *args: Any, **kwargs: Any) -> None:
        """Same as cli_ui.info_count(), except this is a no-op if the
        task is run in parallel with other tasks.

        """
        if not self.parallel:
            ui.info_count(index, count, *args, **kwargs)

    def run_git(self, working_path: Path, *args: str) -> None:
        """Same as tsrc.git.run_git, except the output of the git command
        is captured if the task is run in parallel with other tasks.
        """
        if self.parallel:
            run_git(working_path, *args, verbose=False)
        else:
            run_git(working_path, *args)

    @abc.abstractmethod
    def describe_item(self, item: T) -> str:
        """Return a short description of the item"""
        pass

    @abc.abstractmethod
    def describe_process_start(self, item: T) -> List[ui.Token]:
        """Describe start of the process - when the task is run in parallel"""
        pass

    @abc.abstractmethod
    def describe_process_end(self, item: T) -> List[ui.Token]:
        """Describe end of the process - when the task is run in parallel"""
        pass

    @abc.abstractmethod
    def process(self, index: int, count: int, item: T) -> Outcome:
        """
        Daughter classes should override this method to provide the code
        that processes the item.

        Instances can use self.parallel to know whether they are run
        in parallel with other instances.

        Note: you should use self.info_* and self.run_git so that
        no output is produced when running tasks in parallel.
        """
        pass


class SequentialExecutor(Generic[T]):
    """Run the task on all items one at a time, while collecting errors that
    occur in the process.
    """

    def __init__(self, task: Task[T]) -> None:
        self.task = task

    def process(self, items: List[T]) -> Dict[str, Outcome]:
        result = {}
        count = len(items)
        for index, item in enumerate(items):
            item_desc = self.task.describe_item(item)
            try:
                outcome = self.task.process(index, count, item)
            except Error as e:
                ui.error(e)
                outcome = Outcome.from_error(e)
            result[item_desc] = outcome
        return result


class ParallelExecutor(Generic[T]):
    """Run the tasks using `n` threads, while collecting errors that
    occur in the process.
    """

    def __init__(self, task: Task[T], num_jobs: int) -> None:
        self.task = task
        self.num_jobs = num_jobs
        self.done_count = 0
        self.lock = Lock()

    def process(self, items: List[T]) -> Dict[str, Outcome]:
        if not items:
            return {}
        result = {}
        with ThreadPoolExecutor(max_workers=self.num_jobs) as executor:
            count = len(items)
            futures_to_item = {
                executor.submit(self.process_item, index, count, item): item
                for (index, item) in enumerate(items)
            }
            for future in as_completed(futures_to_item):
                item = futures_to_item[future]
                item_desc = self.task.describe_item(item)
                try:
                    outcome = future.result()
                except Error as e:
                    outcome = Outcome.from_error(e)
                result[item_desc] = outcome
        erase_last_line()
        return result

    def process_item(self, index: int, count: int, item: T) -> Outcome:
        # We want to keep all output when processing items it parallel on just
        # one line (like ninja-build)
        #
        # To do that, we need a lock on stdout. We also need task.process() to
        # be silent, which should be the case if it is implemented correctly
        tokens = self.task.describe_process_start(item)
        if tokens:
            with self.lock:
                erase_last_line()
                ui.info_count(index, count, *tokens, end="\r")

        result = self.task.process(index, count, item)

        # Note: we don't know if tasks will be finished in the same order
        # they were started, so to keep the output relevant, we need a
        # done_count here.
        self.done_count += 1

        tokens = self.task.describe_process_end(item)
        if tokens:
            with self.lock:
                erase_last_line()
                ui.info_count(self.done_count - 1, count, *tokens, end="\r")
                if self.done_count == count:
                    ui.info()

        return result


def process_items(
    items: List[T], task: Task[T], *, num_jobs: Optional[int] = None
) -> OutcomeCollection:
    if num_jobs:
        res = process_items_parallel(items, task, num_jobs=num_jobs)
    else:
        res = process_items_sequence(items, task)
    return OutcomeCollection(res)


def process_items_parallel(
    items: List[T], task: Task[T], *, num_jobs: int
) -> Dict[str, Outcome]:
    task.parallel = True
    executor = ParallelExecutor(task, num_jobs=num_jobs)
    return executor.process(items)


def process_items_sequence(items: List[T], task: Task[T]) -> Dict[str, Outcome]:
    task.parallel = False
    executor = SequentialExecutor(task)
    return executor.process(items)
