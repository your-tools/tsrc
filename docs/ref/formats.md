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
* `fixed_ref` (optional): Can be a tag like `v0.1` or a hash like `0ab12ef`.
   If `fixed_ref` is set:

    *  When running `tsrc init`: Project will be cloned with the given branch, and then reset to
        the given ref.
    *  When running `tsrc sync`: If the project is clean, project will be reset
        to the given ref, else a warning message will be printed.

* `copy`: (optional): A list of dictionaries with `src` and `dest` keys, like so:


```
repos:
  src: foo
  url: gitlab:proj1/foo
  branch: develop
  copy:
    - src: foo.txt
      dest: top.txt
```

In this case, after `proj1/foo` has been cloned in `<workspace>/foo`,
(using `develop` branch), `foo.txt` will be copied from `proj1/foo/foo.txt` to
`<workspace>/top.txt`. Note that `copy` only works with files, not directories.

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
