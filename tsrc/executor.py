""" Helpers to run thing on multiple repos and collect errors """

import abc

import tsrc


class ExecutorFailed(tsrc.Error):
    pass


# pylint: disable=too-few-public-methods
class Actor(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def process(self, _):
        pass


class SequentialExecutor():
    def __init__(self, actor):
        self.actor = actor
        self.errors = list()

    def process(self, items):
        if not items:
            return True

        self.errors = list()
        for item in items:
            self.process_one(item)

        if self.errors:
            raise ExecutorFailed()

    def process_one(self, item):
        try:
            self.actor.process(item)
        except tsrc.Error as error:
            self.errors.append((item, error))


def run_sequence(items, actor):
    executor = SequentialExecutor(actor)
    return executor.process(items)
