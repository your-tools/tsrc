.. image::  https://raw.githubusercontent.com/TankerHQ/sdk-js/master/src/public/tanker.png
   :target: #readme

|

.. image:: https://img.shields.io/github/license/TankerHQ/tsrc.svg
   :target: https://github.com/TankerHQ/tsrc/blob/master/LICENSE

.. image:: https://github.com/TankerHQ/tsrc/workflows/tests/badge.svg
   :target: https://github.com/TankerHQ/tsrc/actions

.. image:: https://github.com/TankerHQ/tsrc/workflows/linters/badge.svg
   :target: https://github.com/TankerHQ/tsrc/actions

.. image:: https://img.shields.io/codecov/c/github/TankerHQ/tsrc.svg?label=Coverage
   :target: https://codecov.io/gh/TankerHQ/tsrc

.. image:: https://img.shields.io/pypi/v/tsrc.svg
   :target: https://pypi.org/project/tsrc/


tsrc: manage groups of git repositories
========================================

`Overview`_ · `Installation`_ · `Usage example`_ · `Documentation`_ · `Release notes`_ · `Contributing`_ · `License`_

Overview
---------

tsrc is a command-line tool that helps you manage groups of several git repositories.

It can be `seen in action on asciinema.org <https://asciinema.org/a/131625>`_.


Installation
-------------

`tsrc` is `available on pypi <https://pypi.org/project/tsrc>`_ an can be installed via ``pip``. It requires **Python 3.5** or later.


Usage Example
-------------


* Create a *manifest* repository. (``git@example.org/manifest``)

* Push a file named ``manifest.yml`` looking like:

.. code-block:: yaml

    repos:
      - src: foo
        url: git@example.com/foo.git

      - src: bar
        url: git@example.com/bar.git


* Create a new workspace with all the repositories listed in the manifest:

.. code-block:: console

    $ tsrc init git@git.local/manifest.git

    :: Configuring workspace in /path/to/work
    ...
    => Cloning missing repos
    * (1/2) foo
    ...
    * (2/2) bar
    ...
    : Configuring remotes
    Done ✓


* Synchronize all the repositories in the workspace:

.. code-block:: console

    $ tsrc sync
    => Updating manifest
    ...
    :: Configuring remotes
    :: Synchronizing workspace
    * (1/2) foo
    => Fetching origin
    => Updating branch
    Already up to date
    * (2/2) bar
    => Updating branch
    Updating 29ac0e1..b635a43
    Fast-forward
     bar.txt | 1 +
     1 file changed, 1 insertion(+)
     create mode 100644 bar.txt
    Done ✓


Documentation
--------------

For more details and examples, please refer to `tsrc documentation <https://TankerHQ.github.io/tsrc/>`_.

Release notes
-------------

Detailed changes for each release are documented in the `changelog <https://tankerhq.github.io/tsrc/changelog/>`_.

Contributing
------------

We welcome feedback, `bug reports <https://github.com/TankerHQ/tsrc/issues>`_, and bug fixes in the form of `pull requests <https://github.com/TankerHQ/tsrc/pulls>`_.

Detailed instructions can be found `in the documentation <https://tankerhq.github.io/tsrc/contrib/>`_.

License
-------

tsrc is licensed under a `BSD 3-Clause license <https://github.com/TankerHQ/tsrc/blob/master/LICENSE>`_.
