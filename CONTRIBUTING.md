# Development

All the development happens on [GitHub](https://github.com/TankerHQ/tsrc).

Outcome of discussions among maintainers and users of the software are tracked in the [wiki](https://github.com/TankerHQ/tsrc/wiki).


# Reporting bugs and suggesting new features

Feel free to use the [GitHub's bug tracker](https://github.com/TankerHQ/tsrc/issues) to open issues.

If you are reporting a bug, please provide the following information:

* `tsrc` version
* Details about your environment (operating system, Python version)
* The exact command you run
* The full output

Doing so will ensure we can investigate your bug right away.

# Suggesting changes

You are free to open a pull request on GitHub for any feature you'd like.

Before opening a merge request, please read the [code manifesto](https://TankerHQ.github.io/tsrc/code-manifesto).

Note that for your merge request to be accepted, we'll ask that:

* You follow indications from the code manifesto
* All existing linters pass
* All existing tests run
* The new feature comes with appropriate tests

See the [.travis.yml file](https://github.com/TankerHQ/tsrc/blob/master/.travis.yml)
to see what exactly what commands are run and the Python versions we
support.


# Checking your changes

* Install latest [dmenv](https://github.com/TankerHQ/dmenv) version.
* Install development and documentation dependencies:

```console
$ dmenv install
```

* Finally, run:

```console
$ source "$(dmenv show)/bin/activate"
$ python ci/ci.py
```


# Adding documentation

* Follow the steps from the above section to setup your python environment
* Launch the development server locally:

```bash
$ dmenv run mkdocs serve
```

* Edit the markdown files from the `docs/` folder and review the changes in your browser
* Finally, submit your changes by opening a pull request on GitHub
