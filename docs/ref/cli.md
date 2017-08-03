# Command line reference

## Important note

We use the [argparse](https://docs.python.org/3/library/argparse.html) library to
parse command line arguments, so the `--help` messages are always up-to-date,
probably more so that this documentation :)

## General

`tsrc` uses the same "subcommand" pattern as git does.

Options common to all commands are placed right before the command name.

Options after the command name only apply to this command.

For instance:

```console
$ tsrc --verbose sync
$ tsrc init <manifest url>
```

## Available commands


### init

`tsrc init <manifest url>`

Initialized a new workspace.

Arguments:

* `<manifest url>` (required)

### foreach

Two forms:

* `tsrc foreach -- command --opt1 arg1`

    Runs `command --opt1 arg1` in every repository, and report failures
    at the end.

    Note the `--` token to separate options for `command` from options for
    `tsrc`

* `tsrc foreach -c 'command --opt1 arg1'`

    Ditto, but uses a shell. (`/bin/sh` on Linux or macOS, `cmd.exe` on Windows)

### log

`tsrc log --from FROM [--to TO]`

Display a summary of all changes since a given tag.

Arguments:

* `--from` (required: start tag)
* `--to` (optional: end ref, defaults to master)

Note that if no changes are found, the repository will not be displayed at
all.

### push

#### Create a merge request

`tsrc push [--assignee ASSIGNEE]`

You should run this from a repository with the correct branch checked out.

(The command will fail if you run this while on the `master` branch our in
"detached HEAD" mode)

Arguments:

* `--assignee (optional)`: should match the name of an active GitLab user to be
  assigned to the pull request

#### Accept a merge request

`tsrc push --accept`

Tell GitLab to merge the merge request after the CI has passed.

Note that the source branch will get automatically removed

(Which should not matter since all the information about the source branch will
be found in the merge commit)


### status

`tsrc status`

Displays a summary of the status of your workspace:

* Shows dirty repos
* Shows repos not on the expected branch

### sync

`tsrc sync`

Updates all the repositories and shows a summary at the end.

### version

`tsrc version`

Displays `tsrc` version number, along additional data if run from a git clone.
