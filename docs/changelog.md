# Changelog

## v0.2.0 (2017-08-09)

* Support for specifying custom branches in the manifest
* Support for specifying fixed refs (tags or hashes) in the manifest

New syntax is:

```yaml
repos:
  - src: foo
    url: git@gitlab.com:proj/foo
    branch: next

  - src: bar
    url: git@gitlab.com:proj/bar
    branch: master
    ref: v0.1
```

Note that `branch` is still required.

* You can now skip the `dest` part of the `copy` section if `src` and `dest` are
  equal:

```yaml
copy:
  - src:foo

# same thing as
copy:
 - src: foo
   dest: foo
```


## v0.1.4 (2017-08-04)

Support for Python 3.3, 3.4, 3.5 and 3.6

## v0.1.1 (2017-08-02)

First public release
