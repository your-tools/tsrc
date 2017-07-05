tsrc
====

Manage multiple git repos.

Tutorial
---------

* Install ``tsrc`` with ``pip install tsrc```

* Create a *manifest* repository. (``git@example.org/manifest``)

* Push a file named ``manifest.yml`` looking like:

.. code-block:: yaml


    - src: foo
      url: git@example.com/foo.git

    - src: bar
      url: git@example.com/bar.git
      copy:
        - src: bar.txt
          dest: top.txt


* Clone the repositories with:

.. code-block:: console

    $ mkdir workspace
    $ cd workspace
    $ tsrc init git@example/manifest.git

In this example:

* ``foo`` will be cloned in ``<workspace>/foo``
* ``bar`` will be cloned in ``<workspace>/bar``
* The file ``bar.txt`` will be cloned from the ``bar`` repository at the
  top of the workspace, in ``<workspace>/top.txt``


Differences with google repo
-----------------------------

Pros:

* Written in Python3, not Python2
* Uses PEP8 coding style
* Comprehensive test suite
* Uses mostly 'porcelain' commands from git, instead of relying on plumbings
  internals
* Nicer output
* `Gitlab` support


Missing features: (May be implemented in the future)

* No ``-j`` option
* No support for ``gerrit``
