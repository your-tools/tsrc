# Suggesting changes

All the development happens on [GitHub](https://github.com/dmerejkowsky/tsrc).

You are free to open a pull request for anything you want to change on `tsrc`.

In particular, pull requests that implement a prototype for a new
feature are welcome, having "real code" to look at can provide useful
insight, even if the code is not merged after all.

That being said, if you want your pull request to be merged, we'll
ask that:

* The code follows the indications from the [code manifesto](../code-manifesto.md)
* All existing linters pass
* All existing tests run
* The new feature comes with appropriate tests
* The Git History is easy to review

See the [GitHub actions workflows](https://github.com/dmerejkowsky/tsrc/blob/main/.github/workflows)
to see what exactly what commands are run and the Python versions we
support.

Also, if relevant, you will need to:

* update the changelog (in `docs/changelog.md`)
* update the documentation if required


Finally, feel free to add your name in the `THANKS` file ;)

## Checking your changes

* Install latest [poetry](https://python-poetry.org) version.
* Install development and documentation dependencies:

```console
$ poetry install
```

* Run linters and tests:

```console
$ poetry run invoke lint
$ poetry run pytest -n auto
```


## Adding documentation

* Follow the steps from the above section to setup your python environment
* Launch the development server locally:

```bash
$ poetry run mkdocs serve
```

* Edit the markdown files from the `docs/` folder and review the changes in your browser
* Finally, submit your changes by opening a pull request on GitHub
