tsrc
====

.. image:: https://travis-ci.org/TankerApp/tsrc.svg?branch=master
  :target: https://travis-ci.org/TankerApp/tsrc

Manage multiple git repos.

Tutorial
---------

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

* ``foo`` will be cloned in ``<workspace>/foo`` using ``git@example.co:proj1/foo.git`` origin url.
* Similarly, ``bar`` will be cloned in ``<workspace>/bar`` using ``git@example.com:proj2/bar.git``
* The file ``bar.txt`` will be copied from the ``bar`` repository to the
  top of the workspace, in ``<workspace>/top.txt``


Differences with google repo
-----------------------------

Pros:

* Nicer output
* **GitLab** support
* Uses mostly 'porcelain' commands from git, instead of relying on plumbings
  internals
* Comprehensive test suite
* Uses PEP8 coding style
* Written in Python 3, not Python 2


Missing features: (May be implemented in the future)

* No ``-j`` option
* No support for ``gerrit`` or ``github``
