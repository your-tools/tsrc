# Configuration files formats

Unless otherwise noted, all configuration files use [YAML](http://www.yaml.org/)
syntax

## Manifest format

The manifest is always parsed as a dictionary .

### Top fields


* `repos` (required): list of repos to clone

* `gitlab.url` (optional): HTTP URL of the GitLab instance

* `groups` (optional): list of groups

### repos

Each repository is also a dictionary, containing:

* `src` (required): relative path of the repository in the workspace
* `url` (required): URL to use when cloning the repository (usually using ssh)
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
* `copy` (optional): A list of dictionaries with `src` and `dest` keys, like so:

        repos:
          - src: foo
            url: gitlab:proj1/foo
            branch: next

          - src: bar
            url: gitlab:proj1/bar
            branch: master
            sha1: ad2b68539c78e749a372414165acdf2a1bb68203

          - src: app
            url: gitlab:proj1/app
            tag: v0.1
            copy:
              - src: top.cmake
                dest: CMakeLists.txt
              - src: .clang-format

    In this example:

    * First, `proj1/foo` will be cloned into `<workspace>/foo` using the `next` branch.
    * Then, `proj1/bar` will be cloned into `<workspace>/bar` using the `master` branch, and reset to `ad2b68539c78e749a372414165acdf2a1bb68203`.
    * Finally:
        * `proj1/app` will be cloned into `<workspace>/app` using the `v0.1` tag,
        * `top.cmake` will be copied from `proj1/app/top.cmake` to `<workspace>/CMakeLists.txt`, and
        * `.clang-format` will be copied from `proj1/app/` to `<workspace>/`.

    Note that `copy` only works with files, not directories.

## groups

The `groups` section lists the groups by name. They should contain a `repos` field
containing a list of repositories (which should match the sources of the repositories
defined in the `repos`  section.

The groups can optionally include other groups, with a `includes` field which should be
a list of existing group names.

The group named `default`, if it exists, will be used to know which repositories to clone
when using `tsrc init` and the `--group` command line argument is not used.

Example:

```yaml
repos:
  - src: a
    url: ..
  - src: b
    url: ..
  - src: bar
    url: ..
  - src: baz
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





## tsrc.yml format

`tsrc.yml` must be written in `XDG_CONFIG_HOME` (or `~/.config/`).

We use GitLab authentication with token, like so:

```
auth:
  gitlab:
    token: <your token>
```
