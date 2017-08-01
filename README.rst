tsrc
====

.. image:: https://travis-ci.org/TankerApp/tsrc.svg?branch=master
  :target: https://travis-ci.org/TankerApp/tsrc

Manage multiple git repos.

Demo
----

`tsrc demo on asciinema.org <https://asciinema.org/a/131625>`_

Tutorial
---------

Getting started
+++++++++++++++


* Install ``tsrc`` with ``pip install tsrc``

* Create a *manifest* repository. (``git@example.org/manifest``)

* Push a file named ``manifest.yml`` looking like:

.. code-block:: yaml

    clone_prefix: git@example.com

    repos:
      - src: foo
        name: proj1/foo

      - src: bar
        name: proj2/bar
        copy:
          - src: bar.txt
            dest: top.txt


* Clone the repositories with:

.. code-block:: console

    $ mkdir workspace
    $ cd workspace
    $ tsrc init git@example/manifest.git

In this example:

* ``foo`` will be cloned in ``<workspace>/foo`` using ``git@example.com:proj1/foo.git`` origin url.
* Similarly, ``bar`` will be cloned in ``<workspace>/bar`` using ``git@example.com:proj2/bar.git``
* The file ``bar.txt`` will be copied from the ``bar`` repository to the
  top of the workspace, in ``<workspace>/top.txt``

Managing Merge Requests
+++++++++++++++++++++++

* Generate a token from GitLab

* Add the *http* url to the manifest:

.. code-block:: yaml

    gitlab:
      url: http://gitlab.local

* Create a ``~/.config/tsrc.yml`` looking like:

.. code-block:: text

    auth:
      gitlab:
        token: <YOUR TOKEN>


* Start working on your branch

* Create the pull request

.. code-block:: console

    $ tsrc push --assignee <an octive user>

* When the review is done, tell GitLab to merge it once the CI passes

.. code-block:: console

    $ tsrc push --accept


Differences with google repo
-----------------------------

Pros:

* GitLab support
* Nicer output
* Uses mostly 'porcelain' commands from git, instead of relying on plumbings
  internals
* Comprehensive test suite
* Uses PEP8 coding style
* Written in Python 3, not Python 2

Missing features: (May be implemented in the future)

* Cloning a specific branch, revision or tag
* Cloning several repositories in parallel ``-j`` option
* Cloning just one or several groups of repositories
* Support for other hosting services such as ``gerrit`` or ``github``
