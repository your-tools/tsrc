""" Entry point for tsrc sync """

import sys

import tsrc
from tsrc import ui
import tsrc.cli


class RepoSyncer:
    def __init__(self, workspace):
        self.workspace = workspace
        self.manifest = None
        self.bad_branches = list()
        self.errors = list()

    def execute(self):
        self.clone_missing()
        self.sync_repos()
        self.copy_files()
        self.summary()
        return (not self.errors) and (not self.bad_branches)

    def clone_missing(self):
        self.manifest = self.workspace.update_manifest()
        self.workspace.clone_missing(self.manifest)

    def sync_repos(self):
        num_repos = len(self.manifest.repos)
        for i, repo, full_path in self.workspace.enumerate_repos():
            ui.info_count(i, num_repos, "Sync", ui.bold, repo.src)
            self.sync_repo(repo, full_path)

    def sync_repo(self, repo, repo_path):
        tsrc.git.run_git(repo_path, "fetch", "--tags", "--prune", "origin")
        if repo.fixed_ref:
            self.sync_repo_to_ref(repo, repo_path)
        else:
            self.sync_repo_to_branch(repo, repo_path)

    def sync_repo_to_branch(self, repo, repo_path):
        current_branch = None
        try:
            current_branch = tsrc.git.get_current_branch(repo_path)
            tsrc.git.run_git(repo_path, "merge", "--ff-only", "@{u}")
        except tsrc.Error:
            self.errors.append((repo.src, "updating branch failed"))
        if current_branch and current_branch != repo.branch:
            self.bad_branches.append((repo.src, current_branch, repo.branch))

    def sync_repo_to_ref(self, repo, repo_path):
        ui.info_2("Resetting to", repo.fixed_ref)
        status = tsrc.git.get_status(repo_path)
        if status != "clean":
            ui.info("%s, skipping" % status)
            self.errors.append((repo.src, status))
            return
        try:
            tsrc.git.run_git(repo_path, "reset", "--hard", repo.fixed_ref)
        except tsrc.Error:
            self.errors.append((repo.src, "updating ref failed"))

    def copy_files(self):
        self.workspace.copy_files(self.manifest)

    def display_errors(self):
        if self.errors:
            ui.error(ui.cross, "Sync failed")
            for src, error in self.errors:
                ui.info("*", ui.bold, src + ":", ui.red, error)

    def display_bad_branches(self):
        if not self.bad_branches:
            return
        ui.warning("Some projects were not on the correct branch")
        headers = ("project", "actual", "expected")
        data = [
            ((ui.bold, name), (ui.red, actual), (ui.green, expected)) for
            (name, actual, expected) in self.bad_branches
        ]
        ui.info_table(data, headers=headers)

    def summary(self):
        self.display_bad_branches()
        self.display_errors()


def main(args):
    workspace = tsrc.cli.get_workspace(args)
    repo_syncer = RepoSyncer(workspace)
    ok = repo_syncer.execute()
    if ok:
        ui.info("Done", ui.check)
    else:
        sys.exit(1)
