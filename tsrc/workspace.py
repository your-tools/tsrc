""" Tools to manage tsrc workspaces

Mostly used by tsrc/cli.py

"""

import stat

from tsrc import ui
import tsrc
import tsrc.git
import tsrc.manifest


class Workspace():
    def __init__(self, root_path):
        self.root_path = root_path
        hidden_path = self.joinpath(".tsrc")
        self.manifest_clone_path = hidden_path.joinpath("manifest")

    def joinpath(self, *parts):
        return self.root_path.joinpath(*parts)

    def load_manifest(self):
        manifest_yml_path = self.manifest_clone_path.joinpath("manifest.yml")
        if not manifest_yml_path.exists():
            message = "No manifest found in {}. Did you run `tsrc init` ?"
            raise tsrc.Error(message.format(manifest_yml_path))
        manifest = tsrc.manifest.Manifest()
        manifest.load(manifest_yml_path.text())
        return manifest

    def get_gitlab_url(self):
        manifest = self.load_manifest()
        gitlab_config = manifest.gitlab
        if not gitlab_config:
            raise tsrc.Error("No gitlab configuration found in manifest")
        res = gitlab_config.get("url")
        if not res:
            raise tsrc.Error("Missing 'url' in gitlab configuration")
        return res

    def init_manifest(self, manifest_url, *, branch="master", tag=None):
        if self.manifest_clone_path.exists():
            ui.warning("Re-initializing worktree")
            tsrc.git.run_git(self.manifest_clone_path,
                             "remote", "set-url", "origin",
                             manifest_url)

            tsrc.git.run_git(self.manifest_clone_path, "fetch")
            tsrc.git.run_git(self.manifest_clone_path, "checkout",
                             "-B", branch)
            tsrc.git.run_git(self.manifest_clone_path, "branch",
                             branch, "--set-upstream-to", "origin/%s" % branch)
            if tag:
                ref = tag
            else:
                ref = "origin/%s" % branch
            tsrc.git.run_git(self.manifest_clone_path, "reset", "--hard", ref)
        else:
            parent, name = self.manifest_clone_path.splitpath()
            parent.makedirs_p()
            tsrc.git.run_git(self.manifest_clone_path.parent, "clone",
                             manifest_url, name, "--branch", branch)
            if tag:
                tsrc.git.run_git(self.manifest_clone_path, "reset",
                                 "--hard", tag)

        return self.load_manifest()

    def update_manifest(self):
        ui.info_2("Updating manifest")
        if not self.manifest_clone_path.exists():
            message = "Could not find manifest in {}. "
            message += "Did you run `tsrc init` ?"
            raise tsrc.Error(message.format(self.manifest_clone_path))
        cmd = ("fetch", "--prune", "origin")
        tsrc.git.run_git(self.manifest_clone_path, *cmd)
        cmd = ("reset", "--hard", "@{u}")
        tsrc.git.run_git(self.manifest_clone_path, *cmd)
        return self.load_manifest()

    def manifest_branch(self):
        return tsrc.git.get_current_branch(self.manifest_clone_path)

    def clone_missing(self, manifest):
        """ Clone missing repos.

        Called at the beginning of `tsrc init` and `tsrc sync`

        """
        to_clone = list()
        for (src, url) in manifest.repos:
            repo_path = self.joinpath(src)
            if not repo_path.exists():
                to_clone.append((src, url))
        num_repos = len(to_clone)
        for i, (src, url) in enumerate(to_clone):
            repo_path = self.joinpath(src)
            parent, name = repo_path.splitpath()
            parent.makedirs_p()
            ui.info_count(i, num_repos, "Cloning", ui.bold, src)
            tsrc.git.run_git(parent, "clone", url, "--branch", "master", name)

    def set_remotes(self):
        ui.info_1("Setting remote URLs")
        manifest = self.load_manifest()
        for src, url in manifest.repos:
            full_path = self.joinpath(src)
            _, old_url = tsrc.git.run_git(full_path, "remote", "get-url", "origin", raises=False)
            if old_url != url:
                ui.info_2(src, old_url, "->", url)
                tsrc.git.run_git(full_path, "remote", "set-url", "origin", url)

    def copy_files(self, manifest):
        for src, dest in manifest.copyfiles:
            src_path = self.joinpath(src)
            dest_path = self.joinpath(dest)
            ui.info_2("Copying", src, "->", dest)
            if dest_path.exists():
                # Re-set the write permissions on the file:
                dest_path.chmod(stat.S_IWRITE)
            src_path.copy(dest_path)
            # Make sure perms are read only for everyone
            dest_path.chmod(0o10444)

    def enumerate_repos(self):
        """ Yield (index, src, full_path) for all the repos """
        manifest = self.load_manifest()
        for i, (src, _) in enumerate(manifest.repos):
            full_path = self.joinpath(src)
            yield (i, src, full_path)

    def get_url(self, src):
        """ Return the url of the project in `src` """
        manifest = self.load_manifest()
        return manifest.get_url(src)
