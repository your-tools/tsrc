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


When the review is done, you can accept it and let GitLab merge the branch once
the CI pipeline passes with the following command:

```bash
$ tsrc push --accept
```
