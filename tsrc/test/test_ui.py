import io
import operator
from unittest import mock

from tsrc import ui

import pytest

RED = "\x1b[31;1m"
GREEN = "\x1b[32;1m"
RESET = "\x1b[0m"
BOLD = "\x1b[1m"
BEGIN_TITLE = "\x1b]0;"
END_TITLE = "\x07"


def assert_equal_strings(a, b):
    return a.split() == b.split()


@pytest.fixture
def smart_tty():
    res = io.StringIO()
    res.isatty = lambda: True
    return res


@pytest.fixture
def dumb_tty():
    res = io.StringIO()
    res.isatty = lambda: True
    return res


def test_info_stdout_is_a_tty(smart_tty):
    ui.info(ui.red, "this is red", ui.reset,
            ui.green, "this is green",
            fileobj=smart_tty)
    expected = (RED + "this is red " + RESET +
                GREEN + "this is green" + RESET + "\n")
    actual = smart_tty.getvalue()
    assert_equal_strings(actual, expected)


def test_update_title(smart_tty):
    ui.info("Something", ui.bold, "bold", fileobj=smart_tty, update_title=True)
    expected = (BEGIN_TITLE + "Something bold" + END_TITLE +
                "Something " + BOLD + "bold" + RESET + "\n")
    actual = smart_tty.getvalue()
    assert_equal_strings(actual, expected)


def test_info_stdout_is_not_a_tty(dumb_tty):
    ui.info(ui.red, "this is red", ui.reset,
            ui.green, "this is green",
            fileobj=dumb_tty)
    expected = "this is red this is green\n"
    actual = dumb_tty.getvalue()
    assert_equal_strings(actual, expected)


def test_info_characters(smart_tty):
    ui.info("Doing stuff", ui.ellipsis, "sucess", ui.check, fileobj=smart_tty)
    actual = smart_tty.getvalue()
    expected = "Doing stuff " + RESET + "…" + " sucess " + GREEN + "✓"
    assert_equal_strings(actual, expected)


def test_ask_choice():
    class Fruit:
        def __init__(self, name, price):
            self.name = name
            self.price = price

    def func_desc(fruit):
        return fruit.name

    fruits = [Fruit("apple", 42), Fruit("banana", 10), Fruit("orange", 12)]
    with mock.patch('builtins.input') as m:
        m.side_effect = ["nan", "5", "2"]
        actual = ui.ask_choice("Select a fruit", fruits,
                               desc_func=operator.attrgetter("name"))
        assert actual.name == "banana"
        assert actual.price == 10
        assert m.call_count == 3


def test_ask_choice_empty_input():
    with mock.patch('builtins.input') as m:
        m.side_effect = [""]
        res = ui.ask_choice("Select a animal", ["cat", "dog", "cow"])
        assert res is None
