## Creating a manifest

`tsrc` is driven by a manifest file that contains the names and paths of repositories to use.

It is a YAML file that looks like this:

```yaml
repos:
  - url: git@gitlab.local:acme/foo
    dest: foo

  - url: git@gitlab.local:acme/bar
    dest: bar
```

!!! note
    The full manifest file format is described in the [reference](../ref/formats.md).

The manifest *must* be stored in its own git repository, so that changes in the
manifest can be tracked like any other code change. The file *must* be named `manifest.yml`

## Cloning a set of repositories

Once the manifest repository is ready, you can run the following commands to create a new workspace:

```bash
$ mkdir ~/work
$ cd work

$ tsrc init git@gitlab.local:acme/manifest.git
```

In this example:

* `tsrc` will record the manifest URL in `.tsrc/config.yml`.
* Then it will clone the manifest inside `.tsrc/manifest`
* Then `foo` will be cloned in `<work>/foo` using `git@gitlab.local/acme/foo.git` as the `origin` remote URL.
* Similarly, `bar` will be cloned in `<work>/bar` using `git@gitlab.local:acme/bar.git`.



## Making sure all the repositories are up to date

You can update all the repositories by using `tsrc sync`.

* First, the manifest clone is updated to match the latest commit on the manifest repository.
* If new repositories have been added to the manifest, they will be cloned.
* Finally, all repositories are *synced*.

The `sync` algorithm looks like this:

* Run `git fetch --tags --prune`
* Check if the repository is on a branch
* Check if the currently checked out branch matches the one configured in
  the manifest
* Check if the repository is dirty
* Try and run a fast-forward merge



Note that:

* `git fetch` is always called so that local refs are up-to-date
* `tsrc` will simply print an error and move on to the next repository if the
  fast-forward merge is not possible. That's because `tsrc` cannot guess
  what the correct action is, so it prefers doing nothing. It's up
  to the user to run something like `git merge` or `git rebase`.
