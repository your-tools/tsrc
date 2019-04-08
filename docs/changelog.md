# Next release

* Remove support for Python 3.4

# v0.6.6 (2019-04-02)

* Remove raw HTML from README.rst

# v0.6.5 (2019-04-0)

* Use `codecov.io` to measure coveage
* Prettify README

# v0.6.4 (2019-01-07)

* Remove support for Python 3.3.
* Use new and shiny [cli-ui](https://pypi.org/project/cli-ui/) package instead of old `python-cli-ui`.

# v0.6.3 (2018-11-04)

* GitHub organization is now `TankerHQ`
* We now use [dmenv](https://github.com/TankerHQ/dmenv) for dependencies management

# v0.6.2 (2018-10-19)

Fix crash when using `tsrc push` on a GitHub repository for the first time.

# v0.6.1 (2018-10-10)

Fix weird output when configuring remotes.

# v0.6.0 (2018-10-09)

## Highlights

## Add support for multiple remotes

```yaml
# still valid (implicit 'origin' remote)
src: foo
url: git@github.com/foo

# also valid (two explicit remotes)
src: fooo
remotes:
  - { name: origin, url: git@github.com:john/foo }
  - { name: upstream, url: git@github.com:foo/foo}

# not valid (ambiguous)
src: foo
url: git@github.com:john/foo
remotes:
   - { name: upstream, url: git@github.com:foo/foo }
```

Thanks @tst2005 and @cgestes for their help with the configuration format.


## tsrc foreach

* `tsrc foreach`: add a `--group` option to select the repositories to run the command on. Fix #40

## Other fixes

* Fix [#113](https://github.com/TankerHQ/tsrc/issues/113): do not hide branch when showing tag status.
* Add support for Python 3.7

# v0.5.0 (2018-08-14)

* Add support for setting approvers with the `-r,--approvers` option in `tsrc push` (GitLab Enterprise Edition only).


# v0.4.1 (2018-04-27)

* Fixed regression: `tsrc push` was no longer able to create a merge request on GitLab if `--target` was not set.

# v0.4.0 (2018-04-26)

## Highlights

* Preliminary GitHub support
* `tsrc push`: new features and bug fixes
* Improved fixed reference handling
* Support for shallow clones

See below for the details.

## Preliminary GitHub support

* Added support for creating merge requests on GitHub. No configuration required. Just make sure you are using `tsrc` from a repository which has a URL starting with `git@github.com`.

`tsrc` will prompt you once for your login and password and then store an API token.

Afterwards, you'll be able to use `tsrc` push to:

* Create a pull request (or update it if it already exists)
* Assign people to the request (with the `-a/--assignee` option)
* Request reviewers (with the `--reviewers` option)
* Merge the pull request (with the `--merge` option)

This change has no impact if you were already using `GitLab`.

## `tsrc push`: new features and bug fixes

* Add ``--close`` option.
* **Breaking change**: `-m/--message` option is gone, use `--title` instead. There's a concept of "description" or "message" for pull requests and merge requests, but the value of the option was only used to update the *title*, so it had to be renamed.
* Do not assume local and remote tracking branch have the same name.
* Allow using `tsrc push <local>:<remote>` to explicitly specify local and remote branch names.
* Fix bugs when target is not specified on the command line. See [this commit](https://github.com/TankerHQ/tsrc/pull/107/commits/5940f96284fe13d9977fafbb05fcc3dad15ac32d) for details.
* Fix missing merge requests in `tsrc push` (see [issue #80](https://github.com/TankerHQ/tsrc/issues/80)). Patch by @maximerety.


## Improve fixed reference handling

**Breaking change**: Instead of using `fixed_ref` in the manifest, you should now use `tag` or `sha1`:

*old*:
```yaml
repos:
  - src: git@example.com/foo
    fixed_ref: 42a70
```

*new*:
```
repos:
  - src: git@example.com/foo
    tag: v0.1
```

See the [dedicated section about manifest format](ref/formats.md#repos) and the [#57 pull request discussion](https://github.com/TankerHQ/tsrc/pull/57) for the details.

This allow us to implement different behaviors depending on whether or not the fixed ref is a tag or just a sha1.

## Support for shallow clones

To save time and space, you can use `tsrc init --shallow` to only have shallow clones in your workspace.

Note that due to limitations in `git` itself, the `shallow` option cannot be used with a fixed SHA1. If you need this, prefer using a `tag` instead.


## Misc

* Organization `TankerApp` was renamed to `TankerHQ`. New urls are:

    * [github.com/TankerHQ/tsrc](https://github.com/TankerHQ/tsrc) for the git repository
    * [TankerHQ.github.io/tsrc](https://TankerHQ.github.io/tsrc) for the documentation


* We now use [pipenv](https://docs.pipenv.org/) for dependency handling.

# v0.3.2 (2017-11-02)

* Improve `tsrc status` to handle tags. Patch by @arnaudgelas.
* Fix crash when running `tsrc version`.

# v0.3.1 (2017-10-06)

* Improve `tsrc status` output. Now also shows number of commits ahead and behind, and display a short SHA-1 when not on any branch. Initial patch by @arnaudgelas.

# v0.3.0 (2017-09-22)


*Breaking change*: Add support for groups (#30). Reported by @arnaudgelas.

See the [dedicated section about manifest format](ref/formats.md#groups) for details.

**Upgrading from v0.2.4**:

To upgrade from an older version of `tsrc`, you should re-run `tsrc init` with the correct url:

```console
# Check manifest URL:
$ cd <workspace>/.tsrc/manifest
$ git remote get-url origin
# Note the url, for instance ssh://git@example.com:manifest.git
$ cd <workspace>
$ tsrc init <manifest-url>
```

This is required to create the `<workspace>/.tsrc/manifest.yml` file which is later used by `tsrc sync` and other commands.


# v0.2.4 (2017-07-13)

* `tsrc push --assignee`: fix when there are more than 50 GitLab users (#25). Reported by @arnaudgelas

# v0.2.3 (2017-09-01)

* Split user interface functionality into its own project: [python-cli-ui](https://github.com/TankerHQ/python-cli-ui).

* Add `--quiet` and `--color` global options.

# v0.2.2 (2017-08-22)

Bug fix release.

* `tsrc init`: Fix crash when a repository is empty (#17). Reported by @nicolasbrechet
* `tsrc push`: Fix rude message when credentials are missing (#20). Reported by @cgestes

# v0.2.1 (2017-08-10)

Packaging fixes.


# v0.2.0 (2017-08-09)

* Support for specifying custom branches in the manifest
* Support for specifying fixed refs (tags or hashes) in the manifest

New syntax is:

```yaml
repos:
  - src: foo
    url: git@gitlab.com:proj/foo
    branch: next

  - src: bar
    url: git@gitlab.com:proj/bar
    branch: master
    fixed_ref: v0.1
```

Note that `branch` is still required.

* You can now skip the `dest` part of the `copy` section if `src` and `dest` are
  equal:

```yaml
copy:
  - src:foo

# same thing as
copy:
 - src: foo
   dest: foo
```


# v0.1.4 (2017-08-04)

Support for Python 3.3, 3.4, 3.5 and 3.6

# v0.1.1 (2017-08-02)

First public release
