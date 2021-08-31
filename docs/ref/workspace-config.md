# Workspace configuration

The workspace configuration lies in `<workspace>/.tsrc/config.yml`.  It is
created by `tsrc init` then read by `tsrc sync` and other commands. It can
be freely edited by hand.

Here's an example:

```yaml
manifest_url: git@acme.corp:manifest.git
manifest_branch: master
shallow_clones: false
repo_groups:
- default
clone_all_repos: false
singular_remote:
```


* `manifest_url`: an git URL containing a `manifest.yml` file
* `manifest_branch`: the branch to use when updating the local manifest (e.g, the first step of `tsrc sync`)
* `shallow_clones`: whether to use only shallow clones when cloning missing repositories
* `repo_groups`: the list of groups to use - every mentioned group must be present in the `manifest.yml` file (see above)
* `clone_all_repos`: whether to ignore groups entirely and clone every repository from the manifest instead
* `singular_remote`: if set to `<remote-name>`, behaves as if `tsrc
  sync` and `tsrc init` were called with `--singular-remote remote-. See
  name>` option. See the [Using remotes guide](../guide/remotes.md) for details.
