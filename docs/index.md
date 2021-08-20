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

* ... and many more commands. Run `tsrc help` to list them, or read the [command line reference](/ref/cli.md)

# Tutorial

Interested in using `tsrc` for your own project?

Proceed to the [getting started tutorial](getting-started.md)!

# Useful links

* [FAQ](./faq.md)
* [Changelog](./changelog.md)

# Going further

## Advanced guides

* [Using groups](guide/groups.md)

## Reference

* [File formats](ref/formats.md)
* [Command line interface](ref/cli.md)

## Contributing

* [Using the issue tracker](contrib/issues.md)
* [Suggesting changes](contrib/dev.md)
* [Code Manifesto](./code-manifesto.md)
