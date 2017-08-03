# Configuration file formats

Unless otherwise noted, all configuration files use [YAML](http://www.yaml.org/)
syntax

## Manifest format

The manifest is always parsed as a dictionary .

### Top fields


* `repos` (required): list of repos to clone

* `gitlab.url` (optional): HTTP URL of the GitLab instance

### repos

Each repository is also a dictionary, containing:

* `src` (required): relative path of the repository in the workspace
* `url` (required): URL to use when cloning the repository (usually using ssh)

In addition, the dictionary can contain a list of files to copy:

* `copyfiles`: a list of dictionary with `src` and `dest` keys, like so:

```
repo:
  src: foo
  url: gitlab:proj1/foo
  copyfiles:
    - src: foo.txt
      dest: top.txt
```

In this case, after `proj1/foo` has been cloned in `<workspace>/foo`, `foo.txt`
will be copied from `proj1/foo/foo.txt` to `<workspace>/top.txt`.

## tsrc.yml format

`tsrc.yml` must be written in `XDG_CONFIG_HOME` (or `~/.config/`).

We use GitLab authentication with token, like so:

```
auth:
  gitlab:
    token: <your token>
```
