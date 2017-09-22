# Configuration files formats

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
* `branch` (optional): The branch to use when cloning the repository (defaults
  to `master`)
* `fixed_ref` (optional): Can be a tag like `v0.1` or a hash like `0ab12ef`.
   If `ref` is set:

    *  When running `tsrc init`: Project will be cloned with the given branch, and then reset to
        the given ref.
    *  When running `tsrc sync`: If the project is clean, project will be reset
        to the given ref, else a warning message will be printed.

* `copyfiles`: (optional): A list of dictionaries with `src` and `dest` keys, like so:


```
repos:
  src: foo
  url: gitlab:proj1/foo
  branch: develop
  copyfiles:
    - src: foo.txt
      dest: top.txt
```

In this case, after `proj1/foo` has been cloned in `<workspace>/foo`,
(using `develop` branch), `foo.txt` will be copied from `proj1/foo/foo.txt` to
`<workspace>/top.txt`.

## tsrc.yml format

`tsrc.yml` must be written in `XDG_CONFIG_HOME` (or `~/.config/`).

We use GitLab authentication with token, like so:

```
auth:
  gitlab:
    token: <your token>
```
