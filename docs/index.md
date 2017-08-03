# tsrc - managing multiple git repositories

## What it is

`tsrc` is a command-line tool that helps you manage several git repositories.

We use it at [tanker.io](https://tanker.io) because:

* We have a small, versatile team of developers
* We use several programming languages
* We need a single source of truth for the list of repositories we want to work
  on: their URL, branch and locations should be the same across all the team.
* None on the many existing solutions did fully match our needs.
  (see the [FAQ](faq.md) for more details)

In addition, `tsrc` has some support for interaction with `GitLab` and makes
handling merge requests from the command line possible.
