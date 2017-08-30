# Command line usage

## Important note

We use the [argparse](https://docs.python.org/3/library/argparse.html) library to
parse command line arguments, so the `--help` messages are always up-to-date,
probably more so than this documentation :)

## General

`tsrc` uses the same "subcommand" pattern as git does.

Options common to all commands are placed right before the command name.

Options after the command name only apply to this command.

For instance:

```console
$ tsrc --verbose sync
$ tsrc init MANIFEST_URL
```

## Global options

--verbose
:   show verbose messages

-q.--quiet
:   hide everything except errors and warnings

--color [always|never|auto]
:    control using color for messages (default 'auto', on if stdout is a terminal)

## Usage


tsrc init MANIFEST_URL
:   Initializes a new workspace.

    MANIFEST_URL should be a git URL containing a valid
    `manifest.yml` file.


tsrc foreach -- command --opt1 arg1
:   Runs `command --opt1 arg1` in every repository, and report failures
    at the end.

    Note the `--` token to separate options for `command` from options for
    `tsrc`

tsrc foreach -c 'command --opt1 arg1'
:   Ditto, but uses a shell. (`/bin/sh` on Linux or macOS, `cmd.exe` on Windows)


tsrc log --from FROM [--to TO]
:   Display a summary of all changes since `FROM` (should be a tag),
    to `TO` (defaulting to `master`)

    Note that if no changes are found, the repository will not be displayed at
    all.

tsrc push [--assignee ASSIGNEE]
:   You should run this from a repository with the correct branch checked out.

    (The command will fail if you run this while on the `master` branch or in
    "detached HEAD" mode)

    `ASSIGNEE` is optional and should match the name of an active GitLab user.

    The merge request will get created if no other opened merge request with the same
    branch exists. Otherwise, the existing merge request will be updated.

tsrc push [--ready|--wip]
:   Toggle the *WIP* ("Work In Progress") prefix for the merge request.

tsrc push --accept
:   Tell GitLab to merge the merge request after the CI has passed.

    Note that the source branch will get automatically removed. (Which should
    not matter since all the information about the source branch will
    be found in the merge commit)


tsrc status
:   Displays a summary of the status of your workspace:

    * Shows dirty repos
    * Shows repos not on the expected branch

tsrc sync
:   Updates all the repositories and shows a summary at the end.

tsrc version
:   Displays `tsrc` version number, along additional data if run from a git clone.
