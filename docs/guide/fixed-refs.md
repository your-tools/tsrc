# Using fixed git references

By default, `tsrc sync` synchronize projects using *branches names*.

Usually, one would use the same branch name for several git repositories, like this:

```yaml
repos:
  - dest: foo
    url: git@gitlab.acme.com/your-team/foo
    branch: main

  - dest: bar
    url: git@gitlab.acme.com/your-team/bar
    branch: main
```

The assumption here is that `foo` and `bar` evolve "at the same time", so when the
`main` branch of `foo` is updated, the `main` branch of `bar` much change too.

Sometimes though, this will not be the case. For instance, the `main` branch of the
`bar` repo needs a *specific, fixed version* of `foo` in order to work.

## Using a tag

One way to solve this is to push a v1.0 tag in the `foo` repository, and change
the manifest too look like this:


```diff
repos:
  - dest: foo
    url: git@gitlab.acme.com/your-team/foo
-    branch: main
+    tag: v1.0
```

## Using a sha1

An other way is to put the SHA1 of the relevant git commit in the `foo` repository in the
manifest:


```diff
repos:
  - dest: foo
    url: git@gitlab.acme.com/your-team/foo
    branch: main
+    sha1: ad2b68539c78e749a372414165acdf2a1bb68203
```

## Cloning repos using fixed refs

* If the repo is configured with a tag, `tsrc` will call `git clone
  --branch <tag>` (which is valid)
* Otherwise, `tsrc` will call `git clone`, followed by `git reset --hard <sha1>`

This is because you cannot tell git to use an arbitrary git reference as
start branch when cloning (tags are fine, but sha1s are not).

This also explain why you need both `branch` and `sha1` in the
configuration.


## Synchronizing repos using fixed refs

Here's what `tsrc sync` will do when trying to synchronize a repo
configured with a fixed ref:

* Run `git fetch --tags --prune`
* Check if the repository is clean
* If so, run `git reset --hard <tag or sha1>`
