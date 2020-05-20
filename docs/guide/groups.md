Sometimes it can be necessary to create groups of repositories, especially if the number
of repositories grows and if you have people in different teams work on different repositories.

## Defining groups in the manifest

The first step is to edit the `manifest.yml` file to describe the groups. Here's an
example.

```yaml
repos:
  - {url: git@gitlab.local:acme/one,   dest: one}
  - {url: git@gitlab.local:acme/two,   dest: two}
  - {url: git@gitlab.local:acme/three, dest: three}

groups:
  default:
    g1: [one, two]
    g2: [three]
```

Here we define a `g1` group that contains repositories named `one` and `two`,
and a `g2` group that contains the repository named `three`.

## Using groups in `tsrc init`

If you only need the repositories in the `g1` group you can run:

```
tsrc init git@gitlab.local:acme/manifest --group g1
```

## Updating workspace configuration

Alternatively, you can edit the `.tsrc/config.yml` file, like this:

```yaml
manifest_url: git@gitlab.local:acme/manifest.git
manifest_branch: master
repo_groups:
- g1   # <- specify the list of groups to use
```

You can use this technique to change the groups used in a given workspace -
the above method using `init` only works to *create* new workspaces.

The config file contains other configuration options, which should be
self-describing - if not, head over to the
[configurations format section](../ref/formats.md#workspace_configuration_file).
