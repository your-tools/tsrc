All configuration files use [YAML](http://www.yaml.org/) syntax.

## manifest.yml

The manifest is always parsed as a dictionary.

### Top fields


* `repos` (required): list of repositories to clone
* `groups` (optional): list of groups

### repos

Each repository is also a dictionary, containing:

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
* `copy` (optional): A list of dictionaries with `file` and `dest` keys.

Here's a full example:

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
```

In this example:

* First, `proj1/foo` will be cloned into `<workspace>/foo` using the `next` branch.
* Then, `proj1/bar` will be cloned into `<workspace>/bar` using the `master` branch, and reset to `ad2b68539c78e749a372414165acdf2a1bb68203`.
* Finally:
    * `proj1/app` will be cloned into `<workspace>/app` using the `v0.1` tag,
    * `top.cmake` will be copied from `proj1/app/top.cmake` to `<workspace>/CMakeLists.txt`, and
    * `.clang-format` will be copied from `proj1/app/` to `<workspace>/`.

Note that `copy` only works with files, not directories.

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

Note that `tsrc init` records the names of the groups it was invoked with, so that `tsrc sync` re-uses them later on. This means that if you want to change the groups used, you must re-run `tsrc init` with the new group list.

## Workspace configuration file


The workspace configuration lies in `<workspace>/.tsrc/config.yml`.  It is
created by `tsrc init` then read by `tsrc sync` and other commands. It can
be freely edited by hand.

Here's an example:

```yaml
manifest_url: git@acme.corp:manifest.git
manifest_branch: master
shallow_clones: false
repo_groups:
- default
clone_all_repos: false
```


* `manifest_url`: an git URL containing a `manifest.yml` file
* `manifest_branch`: the branch to use when updating the local manifest (e.g, the first step of `tsrc sync`)
* `shallow_clones`: whether to use only shallow clones when cloning missing repositories
* `repo_groups`: the list of groups to use - every mentioned group must be present in the `manifest.yml` file (see above)
* `clone_all_repos`: whether to ignore groups entirely and clone every repository from the manifest instead
