# Using several remotes

When you specify a repository in the manifest with
just an URL, `tsrc` assumes you want a remote named
origin:

```yaml
repos:
  - dest: foo
    url: git@gitlab.acme.com/your-team/foo

  - dest: bar
    url: git@gitlab.acme.com/your-team/bar
```

But sometimes you need several remotes. Let's see a few use cases.

## Mirroring open-source projects

If you want some repos in your organization to be open source, you may need:

* a remote named 'origin' containing for the private repository on your GitLab instance
* a remote named 'github' for the public repository on GitHub

In that case, you can use an alternative syntax:

```yaml
repos:
  # foo is open source and thus needs two remotes:
  - dest: foo
  - remotes:
    - name: origin
      url: git@gitlab.acme.com/your-team/foo
    - name: github
      url: git@github.com/your-team/foo

  # bar is closed source and thus only needs the
  # default, 'origin' remote:
  - dest: bar
    url: gitlab.acme.com/your-team/bar
```

After this change, when running `tsrc init` or `tsrc sync`, both the `origin` and `github`
remotes will be created in the `foo` repo if they don't exist, and both
remotes will be fetched when using `tsrc sync`.

## Using a VPN

Sometimes you will need two remotes, because depending the physical location of
your developers, they need to use either:

* a 'normal' remote, when they are in the office
* a 'vpn' remote, when they are working at home

In that case, you can create a manifest looking like this:

```yaml
repos:
  - dest: foo
  - remotes:
    - name: origin
      url: git@gitlab.local/your-team/foo
    - name: vpn
      url: git@myvpn.com/gitlab/your-team/foo

  - dest: bar
  - remotes:
    - name: origin
      url: git@gitlab.local/your-team/bar
    - name: vpn
      url: git@myvpn.com/gitlab/your-team/bar
```

Developers can then use the `-r, --singular-remote` option to either use the `origin` or `vpn` when
running `tsrc init` (to create a workspace), or `tsrc sync` (to synchronize it), depending on
their physical location:

```bash
# Init the workspace using the 'vpn' remote
$ tsrc init -r vpn
# Bring back the computer in the office
# Synchronize using the 'origin' remote:
$ tsrc sync -r origin
```

!!!note
    When using this option, `tsrc` expects the remote to be present in the manifest for *all* repositories.

