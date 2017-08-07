# Frequently asked questions

## Why not Python2 support?

We believe Python2 is an inferior language than Python3, and we use many
Python3 features to make the code more readable and robust.

Plus [Python2.7 supports ends in 3 years](
https://www.python.org/dev/peps/pep-0373/#id2).

## Support for older Python3 versions ?

Python3.3 is already quite old (2012).

There are currently no plans to support earlier versions.

## Why not repo?

We used [repo](https://android.googlesource.com/tools/repo/) for a while, but
found that tsrc had both a better command line API and a nicer output.

On a less subjective level:

* Good support for Windows (no need for CygWin or anything like that)

* **GitLab** support (automate working with merge requests)

* Lastly, tsrc tries hard to never do any destructive operation or unexpected
  actions.

    For instance, `tsrc` never puts you in a "detached HEAD" state,
    nor does automatic rebases. It also never touches dirty repos.

    This is achieved by using mostly 'porcelain' commands from git, instead of
    relying on plumbings internals.


Also (and this matters a lot if you think about contribution):

* Comprehensive test suite
* Uses PEP8 coding style
* Written in Python 3, not Python 2

Here are a few features present in repo that are missing from `tsrc`
(but may be implemented in the future)

* Cloning a revision or tag
* Cloning several repositories in parallel
* Cloning just one or several groups of repositories
* Support for other hosting services such as `gerrit` or `github`

## Why not git-subrepo, mu-repo, or gr?

All this projects are fine but did not match our needs:

* [git-subrepo](https://github.com/ingydotnet/git-subrepo) squashes commits, and
  we prefer having normal clones everywhere
* [mu-repo](https://fabioz.github.io/mu-repo/) is nice and contains an
  interesting dependency management feature, but currently we do not need this complexity.

In any case, now that the whole team is using `tsrc` all the time, it's likely
we'll keep using `tsrc` in the future.

## Why not using libgit2 or similar?

`pygit2` now has pre-built wheels for Windows, but not for macOS and Linux.

We prefer to _not_ require compiling `libgit2`.

Also, we prefer calling git "porcelain" commands, both for readability of the
source code and ease of debugging.

## Why do you hide which git commands are run?


It's mainly a matter of not cluttering the output.
We take care of keeping the output of `tsrc` both concise, readable and
informative.

That being said:

* In case a git command fails, we'll display the full command that was run.
* If you still need to see *all* the git commands that are run, we provide a
  `--verbose` flag, like so: `tsrc --verbose sync`


## Why argparse?

See [docopt v argparse](https://dmerej.info/blog/post/docopt-v-argparse/), and
[please don't use click](http://xion.io/post/programming/python-dont-use-click.html)


## Why YAML?

It's nice to read and write, and we use the excellent [ruamel.yaml](
https://yaml.readthedocs.io/en/latest/) which even has round-trip support.

Also, being Python fans, we don't mind the whitespace constraints :P
