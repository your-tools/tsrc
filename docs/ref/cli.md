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

## Goodies

First, note that like `git`, tsrc will walk up the folders hierarchy
looking for a `.tsrc` folder, which means you can run tsrc commands
anywhere in your workspace, not just at the top.

Second, almost all commands run the operation in parallel. For instance,
`tsrc sync` by default will use as many jobs as the number of CPUs
available on the current machine to synchronize the repos in your workspace.
If this behavior is not desired, you can specify a greater (or lower)
number of jobs using something like `tsrc sync -j2`, or disable the
parallelism completely with `-j1`. You can also set the default number
of jobs by using  the `TSRC_PARALLEL_JOBS ` environment variable.

## Global options

--verbose
:   show verbose messages

-q, --quiet
:   hide everything except errors and warnings

--color [always|never|auto]
:    control using color for messages (default 'auto', on if stdout is a terminal)

## Usage


tsrc init MANIFEST_URL [--group GROUP1, GROUP2] [--singular-remote SINGULAR_REMOTE]
:   Initializes a new workspace.

    MANIFEST_URL should be a git URL containing a valid
    `manifest.yml` file.

    The `-g,--groups`  option can be used to specify a list of groups
    to use when cloning repositories.

    The `-r` "inclusive regular expression" and `-i` "exclusive regular expression" options
    can be combined with the group option to filter for repositories within a group. `-r` takes
    precedence if both options are present.

    The `-s,--shallow` option can be used to make shallow clone of all repositories.

    If you want to add or remove a group in your workspace, you can
    edit the configuration file in `<workspace>/.tsrc/config.yml`

    The `-r,--singular-remote` option can be used to set a fixed remote to use when cloning
    and syncing the repositories. If this flag is set, the remote from the manifest
    with the given name will be used for all repos. It is an error if a repo
    does not have this remote specified.


tsrc foreach -- command --opt1 arg1
:   Runs `command --opt1 arg1` in every repository, and report failures
    at the end.

    Note the `--` token to separate options for `command` from options for
    `tsrc`.

tsrc foreach -c 'command --opt1 arg1'
:   Ditto, but uses a shell (`/bin/sh` on Linux or macOS, `cmd.exe` on Windows).


tsrc log --from FROM [--to TO]
:   Display a summary of all changes since `FROM` (should be a tag),
    to `TO` (defaulting to `master`).

    Note that if no changes are found, the repository will not be displayed at
    all.

tsrc status
:   Displays a summary of the status of your workspace:

    * Shows dirty repositories
    * Shows repositories not on the expected branch

tsrc sync [--correct-branch/-c]
:   Updates all the repositories and shows a summary at the end.
    If any of the repositories is not on the configured branch, but it is clean
    and the `--correct-branch`/`-c` flag is set, then the branch is changed to
    the configured one and then the repository is updated. Otherwise that repository
    will not be not updated.

tsrc version
:   Displays `tsrc` version number, along additional data if run from a git clone.

tsrc apply-manifest PATH
:   Apply changes from the manifest file located at `PATH`. Useful to check changes
    in the manifest before publishing them to the manifest repository.
