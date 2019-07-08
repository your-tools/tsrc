# Basic tsrc usage


## Creating a manifest

`tsrc` is driven by a manifest file that contains the names and paths of repositories to use.

It is a YAML file that looks like this:

```yaml
repos:
  - src: foo
    url: git@gitlab.local:acme/foo

  - src: bar
    url: git@gitlab.local:acme/bar
```

!!! note
    The full manifest file format is described in the [reference](../ref/formats.md).

You can put the manifest in two different places:

* The recommended way is to put the manifest inside its own git repository, so that changes in the
  manifest can be tracked like any other code change. The file *must* be named `manifest.yml`

* Alternatively, you can store the manifest in any file on your file system.

## Cloning a set of repositories

Once the manifest is ready, you can run the following commands to create a new workspace:

```bash
$ mkdir ~/work
$ cd work

# When the manifest is inside a git repository:
$ tsrc init git@gitlab.local:acme/manifest.git

# When the manifest is on the file system:
$ tsrc init --file /path/to/manifest.yml
```

In this example:

* If using a git repository, a clone of the manifest repository will be created in a hidden `.tsrc/manifest` folder.
* Otherwise, `tsrc` will write the path of the manifest inside a persistent configuration file.
* Then `foo` will be cloned in `<work>/foo` using `git@gitlab.local/acme/foo.git` as the `origin` remote URL.
* Similarly, `bar` will be cloned in `<work>/bar` using `git@gitlab.local:acme/bar.git`.



## Making sure all the repositories are up to date

You can update all the repositories by using `tsrc sync`.

* If `tsrc init` was called with a git URL, the manifest clone will be updated first.
* Otherwise, `tsrc sync` will read its persistent configuration file and read the manifest
  from the recorded path. **This means that if the manifest file path changes,
  you'll have to re-run `tsrc init` for `tsrc sync` to work**.

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
