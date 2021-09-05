# Manifest configuration

The manifest configuration must be stored in a file named `manifest.yml`, using
[YAML](https://yaml.org) syntax.

It is always parsed as a *mapping*. Here's an example:

```yaml
repos:
  - url: git@gitlab.local:proj1/foo
    dest: foo
    branch: next

  - remotes:
      - name: origin
        url: git@gitlab.local:proj1/bar
      - name: upstream
        url: git@github.com:user/bar
    dest: bar
    branch: master
    sha1: ad2b68539c78e749a372414165acdf2a1bb68203

  - url: git@gitlab.local:proj1/app
    dest: app
    tag: v0.1
    copy:
      - file: top.cmake
        dest: CMakeLists.txt
      - file: .clangformat
    symlink:
      - source: app/some_file
        target: ../foo/some_file
```

In this example:

* First, `proj1/foo` will be cloned into `<workspace>/foo` using the `next` branch.
* Then, `proj1/bar` will be cloned into `<workspace>/bar` using the `master` branch, and reset to `ad2b68539c78e749a372414165acdf2a1bb68203`.
* Finally:
    * `proj1/app` will be cloned into `<workspace>/app` using the `v0.1` tag,
    * `top.cmake` will be copied from `proj1/app/top.cmake` to `<workspace>/CMakeLists.txt`,
    * `.clang-format` will be copied from `proj1/app/` to `<workspace>/`, and
    * a symlink will be created from `<workspace>/app/some_file` to `<workspace>/foo/some_file`.



## Top fields


* `repos` (required): list of repositories to clone
* `groups` (optional): list of groups

## repos

Each repository is also a *mapping*, containing:

* Either:
    * `url` if you just need one remote named `origin`
    * A list of remotes with a `name` and `url`. In that case, the first remote
      will be used for cloning the repository.
* `dest` (required): relative path of the repository in the workspace
* `branch` (optional): The branch to use when cloning the repository (defaults
  to `master`)
* `tag` (optional):
    * When running `tsrc init`: Project will be cloned at the provided tag.
    * When running `tsrc sync`:  If the project is clean, project will be reset
    to the given tag, else a warning message will be printed.
* `sha1` (optional):
    * When running `tsrc init`: Project will be cloned, and then reset to the given sha1.
    * When running `tsrc sync`:  If the project is clean, project will be reset
    to the given sha1, else a warning message will be printed.
* `copy` (optional): A list of mappings with `file` and `dest` keys.
* `symlink` (optional): A list of mappings with `source` and `target` keys.


See the [Using fixed references](../guide/fixed-refs.md) and the [Performing file system operations](../guide/fs.md) guides for details about how and why you would use the `tag`, `sha1`, `copy` or `symlink` fields.

## groups

The `groups` section lists the groups by name. Each group should have a `repos` field
containing a list of repositories (only repositories defined in the `repos` section are allowed).

The groups can optionally include other groups, with a `includes` field which should be
a list of existing group names.

The group named `default`, if it exists, will be used to know which repositories to clone
when using `tsrc init` and the `--group` command line argument is not used.

Example:

```yaml
repos:
  - dest: a
    url: ..
  - dest: b
    url: ..
  - dest: bar
    url: ..
  - dest: baz
    url: ..

groups:
  default:
    repos: [a, b]
  foo:
    repos: [bar, baz]
    includes: [default]
```

```console
$ tsrc init <manifest_url>
# Clones a, b
$ tsrc init <manifest_url> --group foo
# Clones a, b, bar and baz
```

Note that `tsrc init` records the names of the groups it was invoked
with, so that `tsrc sync` re-uses them later on. This means that if you
want to change the groups used, you must re-run `tsrc init` with the new
group list.

!!! note
    More information about how to use groups is available in the [relevant guide](../guide/groups.md).

