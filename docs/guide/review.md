`tsrc` can automate part of the code review process.

You can use it with GitLab or GitHub repositories.

# Handling GitLab merge requests

## Configuration

The first step is to log in to GitLab and get your personal access token.

Then, write a file in `~/.config/tsrc.yml` containing the token:

```yaml
auth:
  gitlab:
    token: <your token>
```

!!! note
    The full config file format is described in the [reference](../ref/formats.md).

The second step is to tell `tsrc` about the HTTP url of your GitLab instance, which is needed to call the [GitLab HTTP API](https://docs.gitlab.com/ce/api/) (currently using version *4*).

This is done in the *manifest* file:

```yaml
gitlab:
  url: http://gitlab.local

repos:
 - ...
```

## Creating and accepting merge requests

Here's how you can create and assign a merge request:

```bash
# start working on your branch
$ tsrc push [--assignee ASSIGNEE]
```

If `ASSIGNEE` is set to a valid GitLab username, it will be used to assign the merge request.


When the review is done, you can accept it and let GitLab merge the branch once
the CI pipeline passes with the following command:

```bash
$ tsrc push --accept
```

# Handling GitHub pull requests

If there is a remote named `origin` and starting with `git@github.com`, `tsrc` will assume you want to use GitHub.

Then, the first time you need access to GitHub API, it will ask for your credentials, generate a token and store it in the `~/.config/tsrc.yml` file.

## Creating a pull request

Here's how to create a pull request and request reviewers:

```bash
# start working on your branch
$ tsrc push [--reviewer REVIEWER] [--assignee ASSIGNEE]
```
Here `REVIEWER` and `ASSIGNEE` should be usernames of members of your organization.

You can specify the `--reviewer` option several times, and you can also assign someone to the pull request with the `--assignee` option.


!!! note
    `tsrc` does not work across repositories yet. See [issue #73](https://github.com/TankerHQ/tsrc/issues/73).


## Merging or closing a pull request


Assuming you are on the correct branch, you can use `tsrc` to either merge or close the pull request, like so:

```bash
# Close
$ tsrc push --close

# Merge
$ tsrc push --merge
```
