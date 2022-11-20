# Sync algorithm

You may have noticed that `tsrc sync` does not just calls `git pull` on every repository.

Here's the algorithm that is used:


* Run `git fetch --tags --prune`
* Check if the repository is on a branch
* Check if the currently checked out branch matches the one configured in
  the manifest. If it does not but the `--correct-branch` flag is set
  and the repository is clean, the branch is changed to the configured one. 
* Check if the repository is dirty
* Try and run a fast-forward merge

Note that:

* `git fetch` is always called so that local refs are up-to-date
* `tsrc` will simply print an error and move on to the next repository if the
  fast-forward merge is not possible. That's because `tsrc` cannot guess
  what the correct action is, so it prefers doing nothing. It's up
  to the user to run something like `git merge` or `git rebase`.
* in case the repository is on an incorrect branch, the fast-forward merge will
  still be attempted, but an error message will be show in the end

