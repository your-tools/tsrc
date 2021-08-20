# About the workspace configuration file

## Creation

The configuration file created by `tsrc init` contains the whole list
of available settings, with their default value, and is
located at `</path/to/workspace/.tsrc/manifest.yml>`.

Note that if you use command-line options when using `tsrc init`, those
will be written in the `.tsrc/config.yml`.

For instance:

```
tsrc init git@github.com:dmerejkowsky/dummy-manifest
```

generates this file:

```yaml
manifest_url: git@github.com:dmerejkowsky/dummy-manifest
manifest_branch: master
repo_groups: []
shallow_clones: false
clone_all_repos: false
singular_remote:
```

But

```
tsrc init git@github.com:dmerejkowsky/dummy-manifest --branch main
```

generates this instead:


```yaml
manifest_url: git@github.com:dmerejkowsky/dummy-manifest
manifest_branch: main
repo_groups: []
shallow_clones: false
clone_all_repos: false
singular_remote:
```

## Editing

You can edit the workspace configuration as you please, for instance
if you need to switch the manifest branch.

If you do so, note that your changes will be taken into account
next time you run `tsrc sync`.
