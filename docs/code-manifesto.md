# Basics

We use `black` to enforce a coding style matching [PEP8](https://www.python.org/dev/peps/pep-0008/).

In addition, every text file must be pushed using UNIX line endings. (On Windows, you are advised to set `core.autocrlf` to `true` in your git config file.)

# Pet peeves

* Prefer double quotes for string literals:

```python
# Yes
def bar():
   """ bar stuff """
   a = "foo"


# No
def bar():
   ''' bar stuff '''
   a = 'foo'

# Exception
my_str = 'It contains some "quotes" inside'
```

* Use the fact that empty data structures are falsy:
```python
# Yes
if not errors:
    ...
# No
if len(errors) == 0:
    ...
```

* Avoid using double negatives:
```python
# Yes
def make_coffee(sugar=False):
    if sugar:
        print("with sugar")

# No
def make_coffee(without_sugar=True):
    if not without_sugar:
        print("with sugar")
```

* Prefer using  "f-strings" if possible, `+` may also work in some contexts.

```python
# Yes
message = f"Welcome {name}!"

# No
message = "Welcome, {}!".format(name)
message = "Welcome, %s!" % name
message = "Welcome, " + name + "!"

# Okayish
with_ext = name + ".txt"
```

* Use `textwrap.dedent()` to build nice-looking multi-lines strings:

```python
# Yes
def foo():
    long_message = textwrap.dedent("""\
        first line
        second line
        third line""")

# No
def foo():
    long_message = """\
first line
second line
third line
"""
```

* Do not initialize several variables on the same line, unless they come from a tuple (for instance the return of a function, or a iteration on a directory)

```python
# Yes
ok, mess  = run_command()

for test_result in test_results:
    outcome, message = res

# No
foo, bar = False, ""

class Foo:
    self.bar, self.baz = None, True
```

* Do not use conditional expressions. The order is not the same as the ternary operator in C++ and JavaScript, so it should be avoided:

```python
# Yes
if foo:
   a = "ok"
else:
   a = "nope"


# No:
a = "ok" if foo else "nope"
```

* Use `if ... in ...` when you can:

```python
# Yes
if value in ["option1", "option2"]:
   ...

# No
if value == "option1" or value == "option2"
  ...
```

# Doc strings and comments in production code

First off, bad comments are worse that no comments.

Also note that you should use comments to explain **why**, never **what**. If the **what** is no clear, it means the behavior of the function or method cannot be easily understood by reading implementation, and so you should fix the implementation instead.

In conclusion, use comments and doc strings sparingly: that way, they will not rot and they will stay useful.

Note: this does not apply for tests (see below).

# Collections


* Use .extend() instead of += to concatenate lists:

```python
# Yes
list_1.extend(list_2)

# No
list_1 += list_2
```
* Only use `list()` and `dict()` to *convert* a value to a list or dict. Prefer literals when possible

```python
# Yes
my_list = []
my_dict = {}

# Also yes:
my_list = list(yield_stuff())

# No
my_list = list()
my_dict = dict()
```

* Also use explicit call to list() in order to make a copy:

```python
# Yes
my_copy = list(my_list)

# Also yes:
my_copy = copy.copy(my_list)

# No
my_copy = my_list[:]
```

* Use list comprehensions instead of loops and "functional" methods:

```python
# Yes
my_list = [foo(x) for x in other_list]

# No
my_list = list()
for x in other_list:
     x.append(foo(x))

# Also no
my_list = map(foo, other_list)

# Yes
even_nums = [x for x in nums if is_even(x)]

# No
even_nums = filter(is_even, nums)
```

* Use iterable syntax instead of building an explicit list:

```python
# Yes
max(len(x) for x in my_iterable)

# No
max([len(x) for x in my_iterable])
```

* Use plural names for collections. This has the nice benefit of allowing you to have meaningful loop names:

```python
for result in results:
   # do something with result
```

# Functions

Prefer using keyword-only parameters when possible:

```python
# Yes
# If the parameter needs a default value:
def foo(bar, *, spam=True):
    ...

# If it does not:
def foo(bar, *, spam):
    ...


# No
def foo(bar, spam=True):
    ...
```

If you use the last form, Python will let you use `foo(42, False)`, and set `spam` to False.
This can cause problems if someone ever changes the `foo` function and adds a new optional argument before `spam`:

```python
def foo(bar, eggs=False, spam=Tue):
    ...
```
After such a change, the line `foo(42, False)` which used to call `foo` with `spam=False` now calls `foo` with `bar=False` and `spam=True`, leading to all kinds of interesting bugs.

Exception to this rule: when the keyword is obvious and will not change:
```python
def get(value, default=None):
  ...
```

# Imports

For any `foo.py` file, `import foo` must never fail, unless there is a necessary module that could not be found. Do not catch  `ImportError` unless it is necessary, for instance to deal with optional dependencies.

```python
import required_module

HAS_NICE_FEATURE = True
try:
    import nice_lib
except ImportError:
    HAS_NICE_FEATURE = False

#...

if HAS_NICE_FEATURE:
    #....
```

* Importing Python files should never cause side effects. It's OK to initialize global variables, but you should never call functions outside a `if __name__ == main() block`.

* Prefer using fully-qualified imports and names:

```python
# Yes
import foo.bar
my_bar = foo.bar.Bar()

# No
from foo import bar
my_bar = bar.Bar()
```

!!! note
    We allow a few exceptions like `from pathlib import Path` or importing classes directory in tests. Use your best judgment.

# Classes

* When you want to make sure a class follows an interface, use `abc.ABCMeta` instead of raising `NotImplementedError`. This way you get the error when the class is instantiated instead of when the method is called.

```python
# Yes
class AbstractFoo(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def foo(self):
        pass


# No
class AbstractFoo:
     def foo(self):
        raise NotImplementedError()

```

* Make sure to use properties when relevant, instead of `get_` methods.

```python
# Yes
class Person:
      def __init__(self, first_name, last_name):
            self.first_name = first_name
            self.last_name = last_name

      @property
      def full_name(self):
          return f"{self.first_name} {self.last_name}"


# No:
class Foo:
      def __init__(self, first_name, last_name):
            self.first_name = first_name
            self.last_name = last_name
            self.full_name = f"{self.first_name} {self.last_name}"
```

For instance, here:

* `full_name` is read-only
* The attribute is automatically updated if `first_name` changes after the object is initialized.

Note that `get_` methods are OK if they do more than simple computations (expensive in time or size, throwing exceptions ...)

# File paths

* If you are manipulating filenames, use the `path.py `library and suffix the variable by `_path`. Avoid using `os.path` or `shutil` methods when `path.py` is better.

```python
# Yes
work_path = Path("foo/work")
work_path.mkdir_p()
foo_path = work_path / "foo.txt"
foo_path.write_text("this is bar")

# No
work_path = os.path.join(foo, "work")
os.path.mkdir(work_path, exist_ok=True)
foo_path = os.path.join(work_path, "foo.txt")
with open(foo_path, "w") as fileobj:
    fileobj.write("this is foo")
```

# Error handling

* All exceptions raised from within `tsrc` should derive from `tsrc.Error`.
* When using external code (from the standard library or a third-party library), you should catch the exceptions and optionally re-raise them.

# Output messages to the user

Do not use `print`, use [python-cli-ui functions](https://TankerHQ.github.io/python-cli-ui#api) instead. This makes it easier to distinguish between real messages and the throw-away `print` statements you add for debugging.

Also, using "high-level" methods such as `ui.info_1()` or `ui.warning()` will make it easier to have a consistent user interface.

# Tests

## Docstrings

If you think the test implementation is complex, add a human-readable description
of the test scenario in the doc string.

For instance:

```python
def test_sync_with_errors(...):
    """" Scenario:
    * Create a manifest with two repos (foo and bar)
    * Initialize a workspace from this manifest
    * Push a new file to the foo repo
    * Create a merge conflict in the foo repo
    * Run `tsrc sync`
    * Check that the command fails and produces the proper error message
    """
```

## Assertions with lists

* Use tuple unpacking to write shorter assertions:

```python
# Yes
actual_list = function_that_returns_list()
(first, second) = actual_list
assert first == something
assert second == something_else

# NO
actual_list = function_that_returns_list()
assert len(actual_list) == 2
first = actual_list[0]
second = actual_list[1]
assert first == something
assert second == something_else
```

## Assertion order

When writing assertions, use the form `assert <actual> == <expected>`:

```python
# Yes
def test_foo():
    assert foo(42) == True

def test_big_stuff():
    actual_result = ...
    expected_result = ...

    assert actual_result == expected_result


# No
def test_foo():
    assert True == foo(42)


def test_big_stuff():
    actual_result = ...
    expected_result = ...

    assert expected_result == actual_result
```

Rationale:

* The `assert(expected, actual)` convention comes from JUnit but we are not writing Java code,
  and besides, the `assert(actual, expected)` convention also exists in other tools.
* `pytest` does not really care, but we prefer being consistent in all tests.
* It's a bit closer to what you would say in English: *"Assert that the result of foo() is 42"*.
