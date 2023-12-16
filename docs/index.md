<img alt="tsrc logo" width="80" src="img/tsrc-logo.png" />

# tsrc - managing groups of git repositories


## What it does

`tsrc` is a command-line tool that helps you manage groups of git repositories.

It works by listing the repositories in a file called `manifest.yml` that looks like this:

```yaml
repos:
  - dest: foo
    url: git@example.com:foo.git

  - dest: bar
    url: git@example.com:bar.git
```

You can then use:

* `tsrc init <manifest url>` to create a *workspace* containing
  the `foo` and `bar` repository

* `tsrc sync` to synchronize all repos in the workspace.

* ... and many more commands. Run `tsrc help` to list them, or read the [command line reference](ref/cli.md)

## Tutorial

Interested in using `tsrc` in your own organization?

Proceed to the [getting started tutorial](getting-started.md)!


## Guides

Once you've learn how to setup tsrc for your organization, feel free to
read the following guides - tsrc supports a variety of use cases beyond
just listing git repositories to be cloned or synchronized and are
described here:

* [Editing the manifest safely](guide/manifest.md)
* [Editing workspace configuration](guide/workspace-config.md)
* [Using groups](guide/groups.md)
* [Using several remotes](guide/remotes.md)
* [Using fixed git references](guide/fixed-refs.md)
* [Performing file system operations](guide/fs.md)
* [Running a command for each repo in the workspace](guide/foreach.md)
* [Using tsrc with continuous integration](guide/ci.md)

### Reference

* [Command line interface](ref/cli.md)
* [Sync algorithm](ref/sync.md)
* [Manifest configuration](ref/manifest-config.md)
* [Workspace configuration](ref/workspace-config.md)

## Contributing

* [Using the issue tracker](contrib/issues.md)
* [Suggesting changes](contrib/dev.md)
* [Code Manifesto](./code-manifesto.md)

## Useful links

* [FAQ](./faq.md)
* [Changelog](./changelog.md)
