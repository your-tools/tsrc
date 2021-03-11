# Development

All the development happens on [GitHub](https://github.com/dmerejkowsky/tsrc).

Outcome of discussions among maintainers and users of the software are tracked in the [wiki](https://github.com/dmerejkowsky/tsrc/wiki).


# Reporting bugs and suggesting new features

Feel free to use the [GitHub's bug tracker](https://github.com/dmerejkowsky/tsrc/issues) to open issues.

If you are reporting a bug, please provide the following information:

* `tsrc` version
* Details about your environment (operating system, Python version)
* The exact command you run
* The full output

Doing so will ensure we can investigate your bug right away.

# Suggesting changes

You are free to open a pull request on GitHub for any feature you'd like.

Before opening a merge request, please read the [code manifesto](https://dmerejkowsky.github.io/tsrc/code-manifesto).

Note that for your merge request to be accepted, we'll ask that:

* You follow indications from the code manifesto
* All existing linters pass
* All existing tests run
* The new feature comes with appropriate tests

See the [GitHub actions workflows](https://github.com/dmerejkowsky/tsrc/blob/master/.github/workflows)
to see what exactly what commands are run and the Python versions we
support.

Also, if relevant, you will need to:

* update the changelog (in `docs/changelog.md`)
* update the documentation if required


Finally, feel free to add your name in the `THANKS` file ;)

# Checking your changes

* Install latest [poetry](https://python-poetry.org) version.
* Install development and documentation dependencies:

```console
$ poetry install
```

* Run linters and tests:

```console
$ ./lint.sh
$ poetry run pytest -n auto
```


# Adding documentation

* Follow the steps from the above section to setup your python environment
* Launch the development server locally:

```bash
$ poetry run mkdocs serve
```

* Edit the markdown files from the `docs/` folder and review the changes in your browser
* Finally, submit your changes by opening a pull request on GitHub
