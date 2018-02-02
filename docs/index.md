# tsrc - managing multiple git repositories

## What it is

`tsrc` is a command-line tool that helps you manage several git repositories.

We use it at [tanker.io](https://tanker.io) because:

* We have a small, versatile team of developers
* We use several programming languages
* We need a single source of truth for the list of repositories we want to work
  on: their URL, branch and locations should be the same across all the team
* None on the many existing solutions did fully match our needs
  (see the [FAQ](faq.md) for more details)

In addition, `tsrc` has some support for interaction with `GitLab` and makes
handling merge requests from the command line possible.

# Installing tsrc

`tsrc` is compatible with **Python 3.4** or higher.

It is available on [pypi](https://pypi.org/project/tsrc/) and can be
installed with [pip](https://pip.pypa.io/en/stable/):

## Linux

```console
$ pip3 install tsrc --user
# Make sure ~/.local/bin is in your PATH
```

## macOS

```console
$ pip3 install tsrc --user
# Make sure ~/Library/Python/3.x/bin is in your PATH
```

## Windows

Install latest Python3 from [python.org/downloads](https://www.python.org/downloads/windows/),
open cmd.exe and run:

```console
$ pip3 install tsrc
```

# Next steps

If `tsrc` is installed properly (check by running `tsrc version`), feel free to
proceed to [basic usage](guide/basics.md).
