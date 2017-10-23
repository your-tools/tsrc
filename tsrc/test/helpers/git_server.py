import ruamel.yaml
import pytest

import tsrc.git


class ManifestHandler():
    def __init__(self, path):
        self.path = path
        self.data = {"repos": list()}

    @property
    def yaml_path(self):
        return self.path.joinpath("manifest.yml")

    def init(self):
        to_write = ruamel.yaml.dump(self.data)
        self.yaml_path.write_text(to_write)
        tsrc.git.run_git(self.path, "add", "manifest.yml")
        tsrc.git.run_git(self.path, "commit", "--message", "Add an empty manifest")
        tsrc.git.run_git(self.path, "push", "origin", "master")

    def add_repo(self, src, url):
        self.data["repos"].append({"url": str(url), "src": src})
        self.push(message="add %s" % src)

    def configure_group(self, name, repos):
        groups = self.data.get("groups")
        if not groups:
            self.data["groups"] = dict()
            groups = self.data["groups"]
        groups[name] = dict()
        groups[name]["repos"] = repos
        self.push(message="add %s group" % name)

    def configure_gitlab(self, *, url):
        self.data["gitlab"] = dict()
        self.data["gitlab"]["url"] = url
        self.push("Add gitlab URL: %s" % url)

    def get_repo(self, src):
        for repo in self.data["repos"]:
            if repo["src"] == src:
                return repo
        assert False, "repo '%s' not found in manifest" % src

    def configue_repo(self, src, key, value):
        repo = self.get_repo(src)
        repo[key] = value
        message = "Change %s %s: %s" % (src, key, value)
        self.push(message)

    def set_repo_url(self, src, url):
        self.configue_repo(src, "url", url)

    def set_repo_branch(self, src, branch):
        self.configue_repo(src, "branch", branch)

    def set_repo_sha1(self, src, ref):
        self.configue_repo(src, "sha1", ref)

    def set_repo_tag(self, src, tag):
        self.configue_repo(src, "tag", tag)

    def set_repo_file_copies(self, src, copies):
        copy_dicts = list()
        for copy_src, copy_dest in copies:
            copy_dicts.append({"src": copy_src, "dest": copy_dest})
        self.configue_repo(src, "copy", copy_dicts)

    def push(self, message):
        to_write = ruamel.yaml.dump(self.data)
        self.yaml_path.write_text(to_write)
        tsrc.git.run_git(self.path, "add", "manifest.yml")
        tsrc.git.run_git(self.path, "commit", "--message", message)
        current_branch = tsrc.git.get_current_branch(self.path)
        tsrc.git.run_git(self.path, "push", "origin", "--set-upstream", current_branch)

    def change_branch(self, branch):
        tsrc.git.run_git(self.path, "checkout", "-B", branch)
        tsrc.git.run_git(self.path, "push", "--no-verify", "origin", "--set-upstream", branch)


class GitServer():
    def __init__(self, tmpdir):
        self.tmpdir = tmpdir
        self.bare_path = tmpdir.joinpath("srv")
        self.src_path = tmpdir.joinpath("src")
        self.add_repo("manifest", add_to_manifest=False)
        self.manifest = ManifestHandler(self.get_path("manifest"))
        self.manifest.init()
        self.manifest_url = self.get_url("manifest")

    def get_path(self, name):
        return self.src_path.joinpath(name)

    def get_url(self, name):
        return str("file://" + self.bare_path.joinpath(name))

    def _create_repo(self, name, empty=False):
        bare_path = self.bare_path.joinpath(name)
        bare_path.makedirs_p()
        tsrc.git.run_git(bare_path, "init", "--bare")
        src_path = self.get_path(name)
        src_path.makedirs_p()
        tsrc.git.run_git(src_path, "init")
        tsrc.git.run_git(src_path, "remote", "add", "origin", bare_path)
        src_path.joinpath("README").touch()
        tsrc.git.run_git(src_path, "add", "README")
        tsrc.git.run_git(src_path, "commit", "--message", "Initial commit")
        if not empty:
            tsrc.git.run_git(src_path, "push", "origin", "master")
        return str(bare_path)

    def add_repo(self, name, add_to_manifest=True, empty=False):
        self._create_repo(name, empty=empty)
        url = self.get_url(name)
        if add_to_manifest:
            self.manifest.add_repo(name, url)
        return url

    def add_group(self, group_name, repos):
        for repo in repos:
            self.add_repo(repo)
        self.manifest.configure_group(group_name, repos)

    def push_file(self, name, file_path, *,
                  contents=None, message=None):
        src_path = self.get_path(name)
        full_path = src_path.joinpath(file_path)
        full_path.parent.makedirs_p()
        full_path.touch()
        if contents:
            full_path.write_text(contents)
        commit_message = message or ("Create/Update %s" % file_path)
        tsrc.git.run_git(src_path, "add", file_path)
        tsrc.git.run_git(src_path, "commit", "--message",
                         commit_message)
        current_branch = tsrc.git.get_current_branch(src_path)
        tsrc.git.run_git(src_path, "push", "origin", "--set-upstream",
                         current_branch)

    def tag(self, name, tag_name):
        src_path = self.get_path(name)
        tsrc.git.run_git(src_path, "tag", tag_name)
        tsrc.git.run_git(src_path, "push", "--no-verify", "origin", tag_name)

    def get_tags(self, name):
        src_path = self.get_path(name)
        rc, out = tsrc.git.run_git(src_path, "tag", raises=False)
        return out

    def get_branches(self, name):
        src_path = self.get_path(name)
        rc, out = tsrc.git.run_git(src_path, "branch", "--list", raises=False)
        return [x[2:].strip() for x in out.splitlines()]

    def get_sha1(self, name):
        src_path = self.get_path(name)
        rc, out = tsrc.git.run_git(src_path, "rev-parse", "HEAD", raises=False)
        return out

    def change_repo_branch(self, name, new_branch):
        src_path = self.get_path(name)
        tsrc.git.run_git(src_path, "checkout", "-B", new_branch)
        tsrc.git.run_git(src_path, "push", "--no-verify",
                         "origin", "--set-upstream", new_branch)

    def delete_branch(self, name, branch):
        src_path = self.get_path(name)
        tsrc.git.run_git(src_path, "push", "origin", "--delete", branch)


@pytest.fixture
def git_server(tmp_path):
    return GitServer(tmp_path)
