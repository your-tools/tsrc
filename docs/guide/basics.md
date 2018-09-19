# Basic tsrc usage


## Cloning a set of repositories

`tsrc` is driven by a manifest file that contains the names and paths of repositories to clone.

It uses the YAML syntax and looks like:

```yaml
repos:
  - src: foo
    url: git@gitlab.local:acme/foo

  - src: bar
    url: git@gitlab.local:acme/bar
```

!!! note
    The full manifest file format is described in the [reference](../ref/formats.md).

The manifest must be put in a git repository too. You can then use the following commands to create a new workspace:

```console
$ mkdir ~/work
$ cd work
$ tsrc init git@gitlab.local:acme/manifest.git
```

In this example:

* A clone of the manifest repository will be created in a hidden `.tsrc/manifest` folder.
* `foo` will be cloned in `<work>/foo` using `git@gitlab.local/acme/foo.git` origin url.
* Similarly, `bar` will be cloned in `<work>/bar` using `git@gitlab.local:acme/bar.git`.


## Making sure all the repositories are up to date

You can update all the repositories by using `tsrc sync`.

* The manifest itself will be updated first.
* If a new repository has been added to the manifest, it will be cloned.
* Lastly, the other repositories will be updated.

Note that `tsrc sync` only updates the repositories if the changes are trivial:

* If the branch has diverged, `tsrc` will do nothing. It's up to you to use
  `rebase` or `merge`.
* Ditto if there is no remote tracking branch.


!!! note
    Like `git`, tsrc will walk up the folders hierarchy looking for a `.tsrc`
    folder, which means you can run tsrc commands anywhere in your workspace, not
    just at the top.
