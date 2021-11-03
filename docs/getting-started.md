# Getting started

## Installing tsrc

The recommended way to install `tsrc` is to use [pipx](https://pypa.github.io/pipx/)

* Make sure to have Python 3.7 or later installed.
* Install pipx
* Run `pipx install tsrc`

You can also install `tsrc` with `pip` if you know what you are doing :)

## Checking tsrc installation

Run:

```
$ tsrc --version
```

## Creating a repository for the manifest

Let's say you are working for the ACME company and you have many git repositories.

You need a tool to track them, so that if a new repository is created, all developers
can get a clone on their development machine quickly, without having to look up its URL
or even *know* it exists.

Also, you need to make sure the repos are cloned in a certain way, so that you can
for instance refer a repo from an other one by using a relative path.

This is where `tsrc` comes in.

The first step is to create *a dedicated repository* for the manifest. I know it may sound
wasteful ("I have already 100 repositories to manage, and you want me to create yet an other one?"),
but, trust me, it's worth it.

So, if your company uses a GitLab instance at `gitlab.acme.com` and you want to crate a manifest
for your team, you may start by creating a new repository at `https://gitlab.acme.com/your-team/manifest`.

Inside this repository, create a file named `manifest.yml` looking like this:

```yaml
repos:
  - dest: foo
    url: git@gitlab.acme.com/your-team/foo

  - dest: bar
    url: git@gitlab.acme.com/your-team/bar
```

Note that this approach works with any king of Git Hosting system, not
just a custom GitLab instance. Just replace `gitlab.acme.com/your-team`
with the correct suffix (like `github.com/your-name/` if you want to
track some repositories from your GitHub account).

## Creating a new workspace

Create a new, empty directory and then run `tsrc init` from it, using the URL of
the manifest created in the above step:

```bash
$ mkdir work
$ cd work
$ tsrc init git@gitlab.acme.com/your-team/manifest.git
```

You should see something like this:

```text
:: Configuring workspace in /path/to/work
Cloning into 'manifest'...
...
=> Cloning missing repos
* (1/2) Cloning foo
Cloning into 'foo'...
...
* (2/2) Cloning bar
Cloning into 'bar'...
...
=> Cloned repos:
* foo cloned from gt@gitlab.acme.com/your-team/foo' (on master)
* bar cloned from gt@gitlab.acme.com/your-team/bar' (on master)
=> Configuring remotes
=> Workspace initialized
=> Configuration written in /path/to/work/.tsrc/config.yml
```

You will notice that:

* The `foo` ad `bar` repositories have been cloned into their respective destination
* A *workspace configuration file* has been created in `/path/to/work/.tsrc/config.yml`. This
  file can be edited by hand to customize `tsrc` behavior. Follow the relevant [guide](guide/workspace-config.md),
  or read the [workspace configuration file reference](ref/workspace-config.md) for more details.

## Updating a new workspace

Now let's assume that Alice created a new commit in `foo`, and Bob a new commit it `bar`, and
that they both pushed them to the `master` branch of the respective repositories.

Now that you have a workspace configured with `tsrc`, you can use `tsrc sync` to retrieve all the changes
in one go:

```bash
$ cd work
$ tsrc sync
```

This time, you should see the following output:

```text
:: Using workspace in /path/to/work
=> Updating manifest
...
=> Cloning missing repos
=> Configuring remotes
=> Synchronizing repos
* (1/2) Synchronizing foo
* Fetching origin
...
   f20af74..aca6c35  master     -> origin/master
* Updating branch: master
Updating f20af74..aca6c35
Fast-forward
 new.txt | 1 +
 1 file changed, 1 insertion(+)
 create mode 100644 new.txt
* (2/2) Synchronizing bar
* Fetching origin
...
   f20af74..02cfef6  master     -> origin/master
* Updating branch: master
Updating f20af74..02cfef6
Fast-forward
 spam.py | 1 +
 1 file changed, 1 insertion(+)
 create mode 100644 spam.py
:: Workspace synchronized
```

Note: `tsrc sync` does not call `git pull` on every repository. The precise algorithm is described
[in the reference documentation](ref/sync.md)

## Adding a new repo to the manifest

Let's say your team now needs a third repository (for instance, at `gitlab.acme.com/your-team/baz`).

Start by making a commit in the `manifest` repository that adds the new repository:

```diff
--- a/manifest.yml
+++ b/manifest.yml
@@ -1,2 +1,3 @@
 repos:
   - dest: foo
     url: git@gitlab.acme.com/your-team/foo

   - dest: bar
     url: git@gitlab.acme.com/your-team/baz

+  - dest: baz
+    url: git@gitlab.acme.com/your-team/baz
```

Then push this commit to the `master` branch of the manifest.

This time when you run `tsrc sync`:

* the `manifest` repository will get updated
* the `baz` repo will be cloned in `/path/to/work/baz`

```bash
$ tsrc sync
```

```text
:: Using workspace in /path/to/work
=> Updating manifest
remote: Enumerating objects: 5, done.
...
Unpacking objects: 100% (3/3), 354 bytes | 354.00 KiB/s, done.
From gitlab.acme.com/your-team/manifest
   63f12d4..bbcd4d9  master     -> origin/master
Reset branch 'master'
...
HEAD is now at bbcd4d9 add baz

=> Cloning missing repos
* (1/1) Cloning baz
Cloning into 'baz'...
...
Receiving objects: 100% (3/3), done.
=> Cloned repos:
* baz cloned from git@gitlab.acme.com/bas (on master)
=> Configuring remotes
=> Synchronizing repos
* (1/3) Synchronizing foo
* Fetching origin
* Updating branch: master
Already up to date.
* (2/3) Synchronizing bar
* Fetching origin
* Updating branch: master
Already up to date.
* (3/3) Synchronizing baz
* Fetching origin
* Updating branch: master
Already up to date.
:: Workspace synchronized
```

## Going further

In this tutorial, we made a lot of assumptions:

* Every repository is using the `master` as the main development branch
* Each repository as only one git remote (the one from `gitlab.acme.com` in our example)
* You're using a manifest just for your team, not the whole company
* ...

`tsrc` can handle all of this use cases, and more. See the other guides for more details.
