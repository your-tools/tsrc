# Performing file system operations

## Introduction

When using `tsrc`, it is assumed that repositories are put in non-overlapping
file system hierarchies, like this:

```text
workspace/
  project_1/
   CMakeLists.txt
    foo.cpp
    bar.cpp
  project_2/
    CMakeLists.txt
    spam.cpp
    eggs.cpp
```

Not like that, where `project_2` is inside a sub-directory of `project_1`:

```text
workspace/
  project_1/
    CMakeLists.txt
    foo.cpp
    bar.cpp
    project_2/
      CMakeLists.txt
      spam.cpp
      eggs.cpp
```

!!! note
    if you really need `project_2` to be a sub-directory of `project_1`,
    consider using *git submodules* instead.

This is usually fine, except when `project_1` and `project_2` share some common configuration.

For instance, you may want to use `clang-format` for both `project_1` and `project_2`.

## Copying a file

One solution is to put the `.clang-format` configuration file in a repo named
`common` and then tell `tsrc` to copy it at the root of the workspace:

```yaml
repos:
  - dest: project_1
    url: git@acme.com:team/project_1

  - dest: project_2
    url: git@acme.com:team/project_2

  - dest: common
    url: git@acme.com:team/commont
    copy:
    - file: clang-format
      dest: .clang-format
```

```bash
$ tsrc sync
=> Cloning missing repos
* (1/1) Cloning common
Cloning into 'common'...
...
=> Performing filesystem operations
* (1/1) Copy /path/to/work/common/clang-format -> /path/to/work/.clang-format
```

Notes:

*  `copy` only works with files, not directories.
* The source path for a copy link is relative to associated repos destination, whereas
  the destination path of the copy is relative to the workspace root.

## Creating a symlink

The above method works fine if the file does not change too often - if not, you may want to create
a symbolic link instead:

```yaml
repos:
  - dest: project_1
    url: git@acme.com:team/project_1

  - dest: project_2
    url: git@acme.com:team/project_2

  - dest: common
    url: git@acme.com:team/commont
    link:
    - source: .clang-format
      target: common/clang-format
```

```bash
$ tsrc sync
=> Cloning missing repos
...
=> Performing filesystem operations
* (1/1) Lint /path/to/work/.clang-format -> common/.clang-format
```

Notes:

* The source path for a symbolic link is relative to the top-level `<workspace>`, whereas
  each target path is then relative to the associated source.  (This path relationship
  is essentially identical to how `ln -s` works on the command line in Unix-like
  environments.)  Multiple symlinks can be specified; each must specify a source and target.

* Symlink creation is supported on all operating systems, but creation of NTFS symlinks on
  Windows requires that the current user have appropriate security policy permission
  (SeCreateSymbolicLinkPrivilege).  By default, only administrators have that privilege set,
  although newer versions of Windows 10 support a Developer Mode that permits unprivileged
  accounts to create symlinks.  Note that Cygwin running on Windows defaults to creating
  links via Windows shortcuts, which do *not* require any special privileges.
  (Cygwin's symlink behavior can be user controlled with the `winsymlinks` setting
  in the `CYGWIN` environment variable.)
