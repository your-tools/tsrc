""" Helpers to run things on multiple repos and collect errors """

import abc

import ui

import tsrc


class ExecutorFailed(tsrc.Error):
    pass


class Task(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def description(self) -> str:
        pass

    # pylint: disable=no-self-use
    def quiet(self):
        return False

    @abc.abstractmethod
    def display_item(self, _) -> str:
        pass

    @abc.abstractmethod
    def process(self, _):
        pass


class SequentialExecutor():
    def __init__(self, task):
        self.task = task
        self.errors = list()

    def process(self, items):
        if not items:
            return True
        ui.info_1(self.task.description())

        self.errors = list()
        num_items = len(items)
        for i, item in enumerate(items):
            if not self.task.quiet():
                ui.info_count(i, num_items, end="")
            self.process_one(item)

        if self.errors:
            self.handle_errors()

    def handle_errors(self):
        ui.error(self.task.description(), "failed")
        for item, error in self.errors:
            item_desc = self.task.display_item(item)
            message = [ui.green, "*", " ", ui.reset, ui.bold, item_desc]
            if error.message:
                message.extend([ui.reset, ": ", error.message])
            ui.info(*message, sep="")
        raise ExecutorFailed()

    def process_one(self, item):
        try:
            self.task.process(item)
        except tsrc.Error as error:
            self.errors.append((item, error))


def run_sequence(items, task):
    executor = SequentialExecutor(task)
    return executor.process(items)
