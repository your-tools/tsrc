# Colorized output to console taken from
# qibuild (github.com/aldebaran/qibuild), BSD license

""" Tools for a nice user interface

"""
# I like the constants in lower-case and the fact they're aligned
# around the '=' sign, so tell pylint to skip this file
# pylint: skip-file

import sys
import time
import os
import datetime
import difflib
import functools
import traceback
import io

import colorama
import unidecode


CONFIG = {
    "verbose": os.environ.get("VERBOSE"),
    "quiet": False,
    "color": os.environ.get("COLOR", "auto"),
    "title": "auto",
    "record": False  # used for testing
}


# used for testing
_MESSAGES = list()

# so that we don't re-compute this variable over
# and over again:
_ENABLE_XTERM_TITLE = None

# should we call colorama.init()?
_INITIALIZED = False


# ANSI color codes, as classes,
# so that we can use ::
#
#  ui.info(ui.bold, "This is bold")


class _Color:
    def __init__(self, code, modifier=None):
        self.code = '\033[%d' % code
        if modifier is not None:
            self.code += ';%dm' % modifier
        else:
            self.code += 'm'


reset     = _Color(0)
bold      = _Color(1)
faint     = _Color(2)
standout  = _Color(3)
underline = _Color(4)
blink     = _Color(5)
overline  = _Color(6)

black      = _Color(30)
darkred    = _Color(31)
darkgreen  = _Color(32)
brown      = _Color(33)
darkblue   = _Color(34)
purple     = _Color(35)
teal       = _Color(36)
lightgray  = _Color(37)

darkgray   = _Color(30, 1)
red        = _Color(31, 1)
green      = _Color(32, 1)
yellow     = _Color(33, 1)
blue       = _Color(34, 1)
fuchsia    = _Color(35, 1)
turquoise  = _Color(36, 1)
white      = _Color(37, 1)

darkteal = turquoise
darkyellow = brown
fuscia = fuchsia

# Other nice-to-have characters:
class _Characters:
    def __init__(self, color, as_unicode, as_ascii):
        if os.name == "nt":
            self.as_string = as_ascii
        else:
            self.as_string = as_unicode
        self.color = color

    def tuple(self):
        return (reset, self.color, self.as_string, reset)


ellipsis = _Characters(reset, "…", "...")
check    = _Characters(green, "✓", "ok")
cross    = _Characters(red,   "❌","ko")

def configure_logging(args):
    verbose = os.environ.get("VERBOSE", False)
    if not verbose:
        verbose = args.verbose
    CONFIG["color"] = args.color
    CONFIG["title"] = args.title
    CONFIG["verbose"] = verbose
    CONFIG["quiet"] = args.quiet


def using_colorama():
    if os.name == "nt":
        if "TERM" not in os.environ:
            return True
        if os.environ["TERM"] == "cygwin":
            return True
        return False
    else:
        return False


def config_color(fileobj):
    from_config = CONFIG["color"]
    if from_config == "never":
        return False
    if from_config == "always":
        return True
    # else: auto
    if os.name == "nt":
        # sys.isatty() is False on mintty, so
        # let there be colors by default. (when running on windows,
        # people can use --color=never)
        # Note that on Windows, when run from cmd.exe,
        # console.init() does the right thing if sys.stdout is redirected
        return True
    else:
        return fileobj.isatty()


def update_title(mystr, fileobj):
    if using_colorama():
        # By-pass colorama bug:
        # colorama/win32.py, line 154
        #   return _SetConsoleTitleW(title)
        # ctypes.ArgumentError: argument 1: <class 'TypeError'>: wrong type
        return
    mystr = '\x1b]0;%s\x07' % mystr
    fileobj.write(mystr)
    fileobj.flush()


def process_tokens(tokens, *, end="\n", sep=" "):
    """ Returns two strings from a list of tokens.
    One containing ASCII escape codes, the other
    only the 'normal' characters

    """
    # Flatten the list of tokens in case some of them are of class _Characters
    flat_tokens = list()
    for token in tokens:
        if isinstance(token, _Characters):
            flat_tokens.extend(token.tuple())
        else:
            flat_tokens.append(token)

    with_color = _process_tokens(flat_tokens, end=end, sep=sep, color=True)
    without_color = _process_tokens(flat_tokens, end=end, sep=sep, color=False)
    return (with_color, without_color)


def _process_tokens(tokens, *, end="\n", sep=" ", color=True):
    res = ""
    for i, token in enumerate(tokens):
        if isinstance(token, _Color):
            if color:
                res += token.code
        else:
            res += str(token)
            if i != len(tokens) -1:
                res += sep
    res += end
    if color:
        res += reset.code
    return res


def message(*tokens, **kwargs):
    """ Helper method for error, warning, info, debug

    """
    if using_colorama():
        global _INITIALIZED
        if not _INITIALIZED:
            if CONFIG["color"] == "always":
                colorama.init(strip=False)
            else:
                colorama.init()
            _INITIALIZED = True
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    fileobj = kwargs.get("fileobj") or sys.stdout
    with_color, without_color = process_tokens(tokens, end=end, sep=sep)
    if CONFIG["record"]:
        _MESSAGES.append(without_color)
    if kwargs.get("update_title") and with_color:
        update_title(without_color, fileobj)
    to_write = with_color if config_color(fileobj) else without_color
    try:
        fileobj.write(to_write)
    except UnicodeEncodeError:
        # Maybe the file descritor does not support the full Unicode
        # set, like stdout on Windows.
        # Use the unidecode library
        # to make sure we only have ascii, while still keeping
        # as much info as we can
        fileobj.write(unidecode.unidecode(to_write))
    fileobj.flush()


def fatal(*tokens, **kwargs):
    """ Print an error message and calls sys.exit """
    error(*tokens, **kwargs)
    sys.exit(1)


def error(*tokens, **kwargs):
    """ Print an error message """
    tokens = [bold, red, "[ERROR]:"] + list(tokens)
    kwargs["fileobj"] = sys.stderr
    message(*tokens, **kwargs)


def warning(*tokens, **kwargs):
    """ Print a warning message """
    tokens = [brown, "[WARN ]:"] + list(tokens)
    kwargs["fileobj"] = sys.stderr
    message(*tokens, **kwargs)


def info(*tokens, **kwargs):
    """ Print an informative message """
    if CONFIG["quiet"]:
        return
    message(*tokens, **kwargs)


def info_1(*tokens, **kwargs):
    """ Print an important informative message """
    info(bold, blue, "::", reset, *tokens, **kwargs)


def info_2(*tokens, **kwargs):
    """ Print an not so important informative message """
    info(bold, blue, "=>", reset, *tokens, **kwargs)


def info_3(*tokens, **kwargs):
    """ Print an even less important informative message """
    info(bold, blue, "*", reset, *tokens, **kwargs)


def info_count(i, n, *rest, **kwargs):
    """ Same as info, but displays a nice counter
    color will be reset
    >>> info_count(0, 4)
    * (1/4)
    >>> info_count(4, 12)
    * ( 5/12)
    >>> info_count(4, 10)
    * ( 5/10)

    """
    num_digits = len(str(n)) # lame, I know
    counter_format = "(%{}d/%d)".format(num_digits)
    counter_str = counter_format % (i+1, n)
    info(green, "*", reset, counter_str, reset, *rest, **kwargs)


def info_progress(prefix, value, max_value):
    """ Display info progress in percent
    :param: value the current value
    :param: max_value the max value
    :param: prefix the prefix message to print

    >>> info_progress("Done", 5, 20)
    Done: 25%

    """
    if sys.stdout.isatty():
        percent = float(value) / max_value * 100
        sys.stdout.write(prefix + ": %.0f%%\r" % percent)
        sys.stdout.flush()


def debug(*tokens, **kwargs):
    """ Print a debug message """
    if not CONFIG["verbose"] or CONFIG["record"]:
        return
    message(*tokens, **kwargs)


def indent_iterable(elems, num=2):
    """Indent an iterable."""
    return [" " * num + l for l in elems]


def indent(text, num=2):
    """Indent a piece of text."""
    lines = text.splitlines()
    return '\n'.join(indent_iterable(lines, num=num))


def tabs(num):
    """ Compute a blank tab """
    return "  " * num


def message_for_exception(exception, message):
    """ Returns a tuple suitable for ui.error()
    from the given exception.
    (Traceback will be part of the message, after
    the ``message`` argument)

    Useful when the exception occurs in an other thread
    than the main one.

    """
    tb = sys.exc_info()[2]
    buffer = io.StringIO()
    traceback.print_tb(tb, file=io)
    return (red, message + "\n",
            exception.__class__.__name__,
            str(exception), "\n",
            reset,
            buffer.getvalue())


class Timer:
    """ To be used as a decorator,
    or as a with statement:

    >>> @Timer("something")
        def do_something():
            foo()
            bar()
    # Or:
    >>> with Timer("something")
        foo()
        bar()

    This will print:
    'something took 2h 33m 42s'

    """
    def __init__(self, description):
        self.description = description
        self.start_time = None
        self.stop_time = None
        self.elapsed_time = None

    def __call__(self, func, *args, **kwargs):
        @functools.wraps(func)
        def res(*args, **kwargs):
            self.start()
            ret = func(*args, **kwargs)
            self.stop()
            return ret
        return res

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *unused):
        self.stop()

    def start(self):
        """ Start the timer """
        self.start_time = datetime.datetime.now()

    def stop(self):
        """ Stop the timer and emit a nice log """
        end_time = datetime.datetime.now()
        elapsed_time = end_time - self.start_time
        elapsed_seconds = elapsed_time.seconds
        hours, remainder = divmod(int(elapsed_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        as_str = "%sh %sm %ss %dms" % (hours, minutes, seconds, elapsed_time.microseconds / 1000)
        info("%s took %s" % (self.description, as_str))


def did_you_mean(message, user_input, choices):
    if not choices:
        return message
    else:
        result = {difflib.SequenceMatcher(a=user_input, b=choice).ratio(): choice \
                  for choice in choices}
        message += "\nDid you mean: %s?" % result[max(result)]
        return message


def read_input():
    """ Read input from the user

    """
    info(green, "> ", end="")
    return input()


def ask_choice(input_text, choices, *, desc_func=None):
    """
    Ask the user to choose from a list of choices.

    `desc_func` will be called on each for displaying and sorting the
    list. If not given, will default to the identity function

    Will loop until:
        * the user enters a valid index
        * or he hits ctrl-c
        * or he leaves the prompt empty

    In the last two cases, None is returned

    """
    if not desc_func:
        desc_func = lambda x: x
    choices.sort(key=desc_func)
    info(green, "::", reset, input_text)
    for i, choice in enumerate(choices, start=1):
        choice_desc = desc_func(choice)
        info("  ", blue, "%i" % i, reset, choice_desc)
    keep_asking = True
    res = None
    while keep_asking:
        try:
            answer = read_input()
        except KeyboardInterrupt:
            return None
        if not answer:
            return None
        try:
            index = int(answer)
        except ValueError:
            info("Please enter a number")
            continue
        if index not in range(1, len(choices)+1):
            info(index, "is out of range")
            continue
        res = choices[index-1]
        keep_asking = False

    return res

if __name__ == "__main__":
    info_1("Info 1")
    info_2("Info 2")
    list_of_things = ["foo", "bar", "baz"]
    for i, thing in enumerate(list_of_things):
        info_count(i, len(list_of_things), thing)
    progress_message = "Done "
    info_progress("Done",  5, 20)
    time.sleep(0.5)
    info_progress("Done", 10, 20)
    time.sleep(0.5)
    info_progress("Done", 20, 20)
    info("\n", check, "done")
    info(cross, "something failed")
