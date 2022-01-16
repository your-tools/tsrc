# Editing the manifest safely

## Introduction: when things go wrong

Let's assume you've successfully implemented `tsrc` for your
organization - now need to make sure to not break anyone's workflow.

Let's see what could go wrong if you make mistakes while editing the
manifest, using a branch called `broken` for the sake of the example).

First, let's see what happens if you break the YAML syntax:

```diff
commit 1633c5a6 (HEAD -> broken, origin/broken)

    Break the manifest syntax

diff --git a/manifest.yml b/manifest.yml
index fe74142..068c35e 100644
--- a/manifest.yml
+++ b/manifest.yml
@@ -1,4 +1,4 @@
-repos:
+repos
   - url: git@github.com:dmerejkowsky/bar.git
     dest: bar
```

After this change is push,  anyone using the `broken` branch of the
manifest will be faced with this kind of error message:

```bash
$ tsrc sync
```

```text
=> Updating manifest
Reset branch 'broken'
Your branch is up to date with 'origin/broken'.
Branch 'broken' set up to track remote branch 'broken' from 'origin'.
HEAD is now at 1633c5a Break the manifest syntax
Error: /path/to/work/.tsrc/manifest/manifest.yml: mapping values are
not allowed here :

      - url: git@gitlab.acme.com:your-team/foo
           ^ (line: 2)

```

Similarly, if you put an invalid URL in the manifest, like this:


```diff
commit ccfb902 (HEAD -> broken, origin/broken)

    Use invalid URL for bar repo

diff --git a/manifest.yml b/manifest.yml
index fe74142..068c35e 100644
--- a/manifest.yml
+++ b/manifest.yml
@@ -1,4 +1,4 @@
repos:
-  - url: git@gitlab.acme.com:your-team/bar
+  - url: git@gitlab.acme.com:your-team/invalid
     dest: bar
```

Users will get:

```bash
$ tsrc sync
```

```text
:: Using workspace in /path/to/work
=> Updating manifest
...
HEAD is now at ccfb902 Use invalid URL
=> Cloning missing repos
=> Configuring remotes
* bar: Update remote origin to new url: (git@acme.com:your-team/invalid.git)
...
=> Synchronizing repos
* (1/2) Synchronizing bar
* Fetching origin
ERROR: Repository not found.
fatal: Could not read from remote repository.

Please make sure you have the correct access rights
and the repository exists.
Error: fetch from 'origin' failed
* (2/2) Synchronizing foo
 ...
Error: Failed to synchronize the following repos:
* bar : fetch from 'origin' failed
```

This will probably not be a huge problem for you, dear reader,
because you know about tsrc's manifest and its syntax.

It *will*, however, be a problem for people who are just using `tsrc`
without knowledge of how it is implemented, because those error messages
will *definitely* confuse them.


## Using the apply-manifest command to avoid breaking developers workflow

If you have a file on your machine containing the manifest changes, you
can use `tsrc apply-manifest` to check those changes against your own
workspace:

```bash
$ cd /path/to/work
$ tsrc apply-manifest /path/to/manifest-repo/manifest.yml
# Check that the changes are OK
# If so, commit and push manifest changes:
$ cd path/to/manifest-repo
$ git commit -a -m "..."
$ git push
# Now you know that everyone can safely run `tsrc sync`
```

## Additional notes

* It is **not** advised to edit the file in
  `.tsrc/manifest/manifest.yml` directly, because `tsrc sync` will
  silently undo any local changes made to this file. This is a known bug,
  see [#279](https://github.com/dmerejkowsky/tsrc/issues/279) for details.


* It is common to place the manifest repo itself in the manifest - so it's easy to edit or read:

```yaml
# In acme.com:your-team/manifest - manifest.yml
repos:
  - url: git@acme.com:your-team/manifest
     dest: manifest

  - url: git@acme.com:your-team/foo
     dest: foo

  - url: git@acme.com:your-team/bar
     dest: bar
```

In that case, you would use:

```
$ tsrc apply-manifest <workspace>/manifest/manifest.yml
```

to check changes before pushing them.

