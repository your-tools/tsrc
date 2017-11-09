# Development

All the development happens on [github](https://github.com/TankerApp/tsrc)

Outcome of discussions among maintainers and users of the software are tracked in the
[wiki](https://github.com/TankerApp/tsrc/wiki)


# Reporting bugs and suggesting new features

Feel free to use [github bug tracker](https://github.com/TankerApp/tsrc/issues) to open issues.

If you are reporting a bug, please provide the following information:

* `tsrc` version
* Details about your environment (operating system, Python version)
* The exact command you run
* The full output

Doing so will ensure we can investigate your bug right away.

# Suggesting changes

You are free to open a pull request on GitHub for any feature you'd like.

Before opening a merge request, please read the [code manifesto](https://tankerapp.github.io/tsrc/code-manifesto)

Note that for your merge request to be accepted, we'll ask that:

* You follow indications from the code manifesto
* All existing linters pass
* All existing tests run
* The new feature comes with appropriate tests

See the [.travis.yml file](https://github.com/TankerApp/tsrc/blob/master/.travis.yml)
to see what exactly what commands are run and the Python versions we
support.


# Checking your changes

* Create a virtualenv
* Activate it
* Install development and documentation dependencies:

```console
$ pip install -r dev-requirements.txt
$ pip install -r doc-requirements.txt
```

* Finally, run:

```console
$ python ci/ci.py
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
