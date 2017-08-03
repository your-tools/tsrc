# Handling GitLab merge requests

The first step is to log in to GitLab and get your personal access token.

Then, write a file in `~/.config/tsrc.yml` containing the token:

```yaml
auth:
  gitlab:
    token: <your token>
```

!!! note
    The full config file format is described in the [reference](../ref/formats.md).

The second step is to tell `tsrc` about the HTTP url of your GitLab instance.

This is used to call the [GitLab HTTP API](https://docs.gitlab.com/ce/api/) (currently using version *4*)

This is done in the *manifest* file:

```yaml
gitlab:
  url: http://gitlab.local

repos:
 - ...
```
