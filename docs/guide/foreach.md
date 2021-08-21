# Running a command for each repo in the workspace

`tsrc` comes with a `foreach` command that allows you to run
the same command for each repo in the workspace.

This can be used for several things. For instance, if you are building
an artifact from a group of repositories, you may want to put a tag on
each repo that was used to produce it:

```bash
$ tsrc foreach git tag v1.2
```

```text
:: Using workspace in /path/to/work
:: Running `git tag v1.1` on 2 repos
/path/to/work/foo $ git tag v1.2
/path/to/work/bar $ git tag v1.2
/path/to/work/baz $ git tag v1.2
OK ✓
```

## Caveats

* If the command you want to run contains arguments starting with&nbsp;`-`: you need
to call `foreach` like this:

```
$ tsrc foreach -- some-command --with-option
```

* By default, the command is passed "as is", without starting a shell. If you want
  to use a shell, use the `-c` option:

```
$ tsrc foreach -c  'echo $PWD'
```

Note that we need single quotes here to prevent the shell from expanding
the `PWD` environment variable when `tsrc` is run.

## Using repo and manifest data

The current `tsrc` implementation may not contain all the features your organization needs.

The good news is that you can extend `tsrc`'s feature set by using `tsrc
foreach`.

Let's take an example, where you have a manifest containing `foo` and `bar` and both
repos are configured to use a `master` branch.

Here's what happens if you run `tsrc sync` with `bar` on the correct branch (`master`), and `foo` on an incorrect branch (`devel`):

```bash
$ tsrc sync
```

```text
:: Using workspace in /path/to/work
=> Updating manifest
...
=> Cloning missing repos
=> Configuring remotes
=> Synchronizing repos
* (1/2) Synchronizing foo
* Fetching origin
* Updating branch: devel
Updating 702f428..2e4fb45
Fast-forward
...
* (2/2) Synchronizing bar
* Fetching origin
* Updating branch: master
Already up to date.
Error: Failed to synchronize the following repos:
* foo : Current branch: 'devel' does not match expected branch: 'master'
```

If this happens with multiple repos, you may want a command to checkout the correct branch automatically.

Here's one way to do it:

```bash
$ tsrc foreach -c 'git checkout $TSRC_PROJECT_MANIFEST_BRANCH'
```

Here we take advantage of the fact that `tsrc` sets the `TSRC_PROJECT_MANIFEST_BRANCH`
environment variable correctly for each repository before running the command.

Here's the whole list:


| Variable                         | Description                                            |
|----------------------------------|--------------------------------------------------------|
| `TSRC_WORKSPACE_PATH`            | Full path of the workspace root                        |
| `TSRC_MANIFEST_BRANCH`           | Branch of the manifest                                 |
| `TSRC_MANIFEST_URL`              | URL of the manifest                                    |
| `TSRC_PROJECT_CLONE_URL`         | URL used to clone the repo                             |
| `TSRC_PROJECT_DEST`              | Relative path of the repo in the workspace             |
| `TSRC_PROJECT_MANIFEST_BRANCH`   | Branch configured in the manifest for this repo        |
| `TSRC_PROJECT_REMOTE_<NAME>`     | URL of the remote named 'NAME'                         |
| `TSRC_PROJECT_STATUS_DIRTY`      | Set to `true` if the project is dirty, otherwise unset |
| `TSRC_PROJECT_STATUS_AHEAD`      | Number of commits ahead of the remote ref              |
| `TSRC_PROJECT_STATUS_BEHIND`     | Number of commits behind the remote ref                |
| `TSRC_PROJECT_STATUS_BRANCH`     | Current branch of the repo                             |
| `TSRC_PROJECT_STATUS_SHA1`       | SHA1 of the current branch                             |
| `TSRC_PROJECT_STATUS_STAGED`     | Number of files that are staged but not committed      |
| `TSRC_PROJECT_STATUS_NOT_STAGED` | Number of files that are changed but not staged        |
| `TSRC_PROJECT_STATUS_UNTRACKED`  | Number of files that are untracked                     |

You can implement more complex behavior using the environment variables above, for instance:

```sh
#!/bin/bash
# in switch-and-pull
if [[ "${TSRC_PROJECT_STATUS_DIRTY}" = "true" ]]; then
  echo Error: project is dirty
  exit 1
fi

git switch $TSRC_PROJECT_MANIFEST_BRANCH
git pull
```

```text
$ tsrc foreach switch-and-pull
:: Running `switch-and-pull` on 2 repos
* (1/2) foo
/path/to/foo $ switch-and-pull
Switched to branch 'master'
Your branch is behind 'origin/master' by 1 commit, and can be fast-forwarded.
  (use "git pull" to update your local branch)
Updating 9e7a8e4..5f9bbd4
Fast-forward
* (2/2) bar
/path/to/bar $ switch-and-pull
Error: project is dirty
Error: Command failed for 1 repo(s)
* bar
```

Of course, feel free to use your favorite programming language here :)
