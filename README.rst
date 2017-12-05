tsrc: manage multiple repos / GitLab automation
===============================================

.. image:: https://img.shields.io/travis/SuperTanker/tsrc.svg?branch=master
  :target: https://travis-ci.org/SuperTanker/tsrc

.. image:: https://img.shields.io/pypi/v/tsrc.svg
  :target: https://pypi.org/project/tsrc/

.. image:: https://img.shields.io/github/license/SuperTanker/tsrc.svg
  :target: https://github.com/SuperTanker/tsrc/blob/master/LICENSE

Demo
----

`tsrc demo on asciinema.org <https://asciinema.org/a/131625>`_

Documentation
--------------

See https://supertanker.github.io/tsrc/

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

* Make sure you are using **Python3.4** or higher.

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

    $ tsrc push --assignee <an active user>

* When the review is done, tell GitLab to merge it once the CI passes::

    $ tsrc push --accept


Why not Google repo?
--------------------

See the `FAQ <https://supertanker.github.io/tsrc/faq/#why_not_repo>`_
