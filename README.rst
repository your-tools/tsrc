tsrc
====

.. image:: https://travis-ci.org/TankerApp/tsrc.svg?branch=master
  :target: https://travis-ci.org/TankerApp/tsrc

.. image:: https://badge.fury.io/py/tsrc.png
  :target: https://pypi.org/project/tsrc/

Manage multiple git repos.

Demo
----

`tsrc demo on asciinema.org <https://asciinema.org/a/131625>`_

Screenshots
-----------

* ``tsrc sync``

.. image:: https://dmerej.info/blog/pics/tsrc-sync.png

* ``tsrc log``

.. image:: https://dmerej.info/blog/pics/tsrc-log.png


Tutorial
---------

Getting started
+++++++++++++++

* Make sure you are using **Python3.5** or higher.

* Install ``tsrc`` with ``pip3`` as usual.

* Create a *manifest* repository. (``git@example.org/manifest``)

* Push a file named ``manifest.yml`` looking like::


    repos:
      - src: foo
        url: git@example.com/foo.git

      - src: bar
        url: git@example.com/bar.git


* Clone the repositories with::


    $ mkdir workspace
    $ cd workspace
    $ tsrc init git@example/manifest.git

In this example:

* ``foo`` will be cloned in ``<workspace>/foo`` using ``git@example.com:foo.git`` origin url.
* Similarly, ``bar`` will be cloned in ``<workspace>/bar`` using ``git@example.com/bar.git``

Managing Merge Requests
+++++++++++++++++++++++

* Generate a token from GitLab

* Add the *http* url to the manifest::

    gitlab:
      url: http://gitlab.local

* Create a ``~/.config/tsrc.yml`` looking like::

    auth:
      gitlab:
        token: <YOUR TOKEN>


* Start working on your branch

* Create the pull request::

    $ tsrc push --assignee <an octive user>

* When the review is done, tell GitLab to merge it once the CI passes::

    $ tsrc push --accept


Differences with google repo
-----------------------------

We used repo for a while, but found that tsrc had both a better command line API
and a nicer output.

On a less subjective level:

* Good support for Windows (no need for cygwin or anything like that)

* tsrc tries hard to never do any destructive operation or unexpected
  actions.

  For instance, ``tsrc`` never puts you in a "detached HEAD" state,
  nor does automatic rebases. It also never touches dirty repos.

  This is achieved by using mostly 'porcelain' commands from git, instead of
  relying on plumbings internals.

* **GitLab** support (automate working with merge requests)

Also (and this matters a lot if you think about contribution):

* Comprehensive test suite
* Uses PEP8 coding style
* Written in Python 3, not Python 2

Here are a few features present in repo that are missing from ``tsrc``
(but may be implemented in the future)

* Cloning a specific branch (but see PR #7)
* Cloning a revision or tag
* Cloning several repositories in parallel
* Cloning just one or several groups of repositories
* Support for other hosting services such as ``gerrit`` or ``github``
