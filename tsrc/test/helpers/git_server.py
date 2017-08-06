import ruamel.yaml
import pytest

import tsrc.git


class GitServer():
    def __init__(self, tmpdir):
        self.tmpdir = tmpdir
        self.manifest_repo = None
        self.manifest_url = None
        self.init_manifest()

    @property
    def manifest_file_path(self):
        return self.manifest_repo.joinpath("manifest.yml")

    def init_manifest(self):
        self.manifest_url = self._add_repo("manifest")
        self.manifest_repo = self.tmpdir.joinpath("src", "manifest")
        self.manifest_file_path.write_text("# Manifest")
        tsrc.git.run_git(self.manifest_repo, "add", "manifest.yml")
        tsrc.git.run_git(self.manifest_repo, "commit", "--message",
                         "Add an empty manifest")
        tsrc.git.run_git(self.manifest_repo,
                         "push", "origin", "master")

    def _add_repo(self, repo_path):
        bare_path = self.tmpdir.joinpath("srv", repo_path + ".git")
        bare_path.makedirs_p()
        tsrc.git.run_git(bare_path, "init", "--bare")
        src_path = self.tmpdir.joinpath("src", repo_path)
        src_path.makedirs_p()
        tsrc.git.run_git(src_path, "init")
        tsrc.git.run_git(src_path, "remote", "add", "origin",
                         bare_path)
        src_path.joinpath("README").touch()
        tsrc.git.run_git(src_path, "add", "README")
        tsrc.git.run_git(src_path, "commit", "--message", "Initial commit")
        tsrc.git.run_git(src_path,
                         "push", "origin", "master")
        return str(bare_path)

    def add_repo(self, repo_path):
        repo_url = self._add_repo(repo_path)
        data = self.get_manifest_data()
        data["repos"].append(
            {
                "url": repo_url,
                "src": repo_path,
            }
        )
        self.push_manifest(data=data, message="add %s" % repo_path)
        return repo_url

    def push_manifest(self, *, data, message):
        self.manifest_file_path.write_text(ruamel.yaml.dump(data))
        tsrc.git.run_git(self.manifest_repo,
                         "add", "manifest.yml")
        tsrc.git.run_git(self.manifest_repo,
                         "commit", "--message", message)
        current_branch = tsrc.git.get_current_branch(self.manifest_repo)
        tsrc.git.run_git(self.manifest_repo,
                         "push",
                         "origin", "--set-upstream", current_branch)

    def get_manifest_data(self):
        empty_manifest = {"repos": list()}
        return ruamel.yaml.safe_load(self.manifest_file_path.text()) or empty_manifest

    def configure_gitlab(self, *, url):
        data = self.get_manifest_data()
        data["gitlab"] = dict()
        data["gitlab"]["url"] = url
        self.push_manifest(data=data, message="Add gitlab URL")

    def push_file(self, repo_path, file_path, *,
                  contents=None, message=None):
        src_path = self.tmpdir.joinpath("src", repo_path)
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

    def tag(self, repo_path, tag_name):
        src_path = self.tmpdir.joinpath("src", repo_path)
        tsrc.git.run_git(src_path, "tag", tag_name)
        tsrc.git.run_git(src_path, "push", "--no-verify", "origin", tag_name)

    def get_tags(self, repo_path):
        git_path = self.tmpdir.joinpath("srv", repo_path + ".git")
        rc, out = tsrc.git.run_git(git_path, "tag", raises=False)
        return out

    def get_branches(self, repo_path):
        git_path = self.tmpdir.joinpath("srv", repo_path + ".git")
        rc, out = tsrc.git.run_git(git_path, "branch", "--list", raises=False)
        return [x[2:].strip() for x in out.splitlines()]

    def change_manifest_branch(self, new_branch):
        tsrc.git.run_git(self.manifest_repo, "checkout",
                         "-B", new_branch)
        tsrc.git.run_git(self.manifest_repo, "push", "--no-verify",
                         "origin", "--set-upstream", new_branch)

    def change_repo_branch(self, repo_path, new_branch):
        src_path = self.tmpdir.joinpath("src", repo_path)
        tsrc.git.run_git(src_path, "checkout", "-B", new_branch)
        tsrc.git.run_git(src_path, "push", "--no-verify",
                         "origin", "--set-upstream", new_branch)

    def delete_branch(self, repo_path, branch):
        src_path = self.tmpdir.joinpath("src", repo_path)
        tsrc.git.run_git(src_path, "push", "origin", "--delete", branch)

    def set_repo_url(self, repo_path, url):
        manifest_data = self.get_manifest_data()
        for repo in manifest_data["repos"]:
            if repo["src"] == repo_path:
                repo["url"] = url
                break
        else:
            assert False, "repo '%s' not found in manifest" % repo_path
        message = "change %s url" % repo_path
        self.push_manifest(data=manifest_data, message=message)

    def set_repo_branch(self, repo_path, branch):
        manifest_data = self.get_manifest_data()
        for repo in manifest_data["repos"]:
            if repo["src"] == repo_path:
                repo["branch"] = branch
                break
        else:
            assert False, "repo '%s' not found in manifest" % repo_path
        self.push_manifest(data=manifest_data, message="change foo url")

    def add_file_copy(self, src, dest):
        if "/" not in src:
            assert False, "src should look like <repo>/<path>, got '%s'" % src
        src_repo, src_cpy = src.split("/", maxsplit=1)
        manifest_data = self.get_manifest_data()
        copy_dict = ({"src": src_cpy, "dest": dest})
        found = False
        for repo in manifest_data["repos"]:
            if repo["src"] == src_repo:
                found = True
                if "copy" in repo:
                    repo["copy"].append(copy_dict)
                else:
                    repo["copy"] = [copy_dict]
        if not found:
            assert False, "repo '%s' not found in manifest" % src_repo
        self.push_manifest(data=manifest_data, message="Add copy: %s -> %s" % (src, dest))


@pytest.fixture
def git_server(tmp_path):
    return GitServer(tmp_path)
