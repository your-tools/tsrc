# Why not repo?

We used [repo](https://android.googlesource.com/tools/repo/) for a while, but
found that tsrc had both a better command line API and a nicer output.

On a less subjective level:

* Good support for Windows (no need for Cygwin or anything like that)

* Also, tsrc tries hard to never do any destructive operation or unexpected
  actions.

    For instance, `tsrc` never puts you in a "detached HEAD" state,
    nor does automatic rebase. It also never touches dirty repositories.

    This is achieved by using mostly 'porcelain' commands from git, instead of
    relying on plumbings internals.


Also (and this matters a lot if you think about contribution):

* Uses PEP8 coding style, enforced with `black`
* Comprehensive test suite
* Fully type-checked with `mypy`

Note that there are a few features present in `repo` that are missing from `tsrc`
(but may be implemented in the future). Feel free to open a feature request
if needed!

# Why not git-subrepo, mu-repo, or gr?

All this projects are fine but did not match our needs:

* [git-subrepo](https://github.com/ingydotnet/git-subrepo) squashes commits, and
  we prefer having normal clones everywhere.
* [mu-repo](https://fabioz.github.io/mu-repo/) is nice and contains an
  interesting dependency management feature, but currently we do not need this complexity.

In any case, now that the whole team is using `tsrc` all the time, it's likely
we'll keep using `tsrc` in the future.

# Why not git submodule?

It's all about workflow.

With `git-submodule`, you have a 'parent' repository and you freeze the state of
the 'children' repositories to a specific commit.

It's useful when you want to re-build a library you've forked when you build
your main project, or when you have a library or build tools you want to
factorize across repositories: this means that each 'parent' repository can
have its children on any commit they want.

With `tsrc`, all repositories are equal, and what you do instead is to make sure
all the branches (or tags) are consistent across repositories.

For instance, if you have `foo` and `bar`, you are going to make sure the
'master' branch of `foo` is always compatible to the 'master' branch of `bar`.

Or if you want to go back to the state of the '0.42' release, you will run:
`tsrc foreach -- git reset --hard v0.42`.

Note that since `tsrc 0.2` you can also freeze the commits of some of the
repositories.

Last but not least, with `tsrc` you do everything with commands like `tsrc
init` and `tsrc sync`, or simple `yaml` files,  which is much easier than
using the `git submodule` CLI.


# Why not using pygit2 or similar instead of running git commands?

First off, we do use `pygit2`, but only for tests.

Second, the `pygit2` package depends on a 3rd party C library (`libgit2`) -
and that can cause problems in certain cases. If we can, we prefer
using pure-Python libraries for the production code.

Finally, we prefer calling git "porcelain" commands, both for readability
of the source code and ease of debugging (see below).

# Why do you hide which git commands are run?

It's mainly a matter of not cluttering the output.
We take care of keeping the output of `tsrc` both concise, readable and
informative.

That being said:

* In case a git command fails, we'll display the full command that was run.
* If you still need to see *all* the git commands that are run, we provide a
  `--verbose` flag, like so: `tsrc --verbose sync`


# Why argh?

Because we need (almost) all of `argparse` features, but still want to keep the
code DRY.


# Why YAML?

It's nice to read and write, and we use the excellent [ruamel.yaml](
https://yaml.readthedocs.io/en/latest/) which even has round-trip support.

Also, being Python fans, we don't mind that white space is part of the syntax.

# Why do I have to create a separate git repo with just one file in it?

See [#235](https://github.com/TankerHQ/tsrc/issues/235) for why you can't
have multiple manifest files in the same repository.

Also, note that you can put other files in the repo - for instance,
add a CI script that verifies the yaml syntax and checks that all the repos
in the manifest can be cloned.
