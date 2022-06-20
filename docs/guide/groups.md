# Using groups

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
    repos: []
  g1:
    repos:
      - one
      - two
  g2:
    repos:
      - three
```

Here we define a `g1` group that contains repositories named `one` and `two`,
and a `g2` group that contains the repository named `three`.

## Using groups in `tsrc init`

If you only need the repositories in the `g1` group you can run:

```
tsrc init git@gitlab.local:acme/manifest --group g1
```

## Filtering repositories in groups with regular expressions

You can utilize inclusive regular expression with the `-r`-flag and
exclusive regular expression with the `-i`-flag. This allows you to filter
repositories within a group or a set of groups for the given action.


To include all repositories in the group g1 matching "config" and excluding "template",
you can do the following:

```
tsrc init git@gitlab.local:acme/manifest --group g1 -r config -i template
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

The config file contains other configuration options, which are described
in the [workspace configuration documentation](../ref/workspace-config.md).
