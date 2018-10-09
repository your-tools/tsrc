from typing import cast, Any, Dict, List, Tuple
import ruamel.yaml
import pytest

import tsrc
import tsrc.git

from path import Path

RepoConfig = Dict[str, Any]
CopyConfig = Tuple[str, str]
RemoteConfig = Tuple[str, str]


class ManifestHandler():
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = {"repos": list()}  # type: Dict[str, Any]

    @property
    def yaml_path(self) -> Path:
        return self.path / "manifest.yml"

    def init(self) -> None:
        to_write = ruamel.yaml.dump(self.data)
        self.yaml_path.write_text(to_write)
        tsrc.git.run(self.path, "add", "manifest.yml")
        tsrc.git.run(self.path, "commit", "--message", "Add an empty manifest")
        tsrc.git.run(self.path, "push", "origin", "master")

    def add_repo(self, src: str, url: str, branch: str = "master") -> None:
        repo_config = ({"url": str(url), "src": src})
        if branch != "master":
            repo_config["branch"] = branch
        self.data["repos"].append(repo_config)
        self.push(message="add %s" % src)

    def configure_group(self, name: str, repos: List[str]) -> None:
        groups = self.data.get("groups")
        if not groups:
            self.data["groups"] = dict()
            groups = self.data["groups"]
        groups[name] = dict()
        groups[name]["repos"] = repos
        self.push(message="add %s group" % name)

    def configure_gitlab(self, *, url: str) -> None:
        self.data["gitlab"] = dict()
        self.data["gitlab"]["url"] = url
        self.push("Add gitlab URL: %s" % url)

    def get_repo(self, src: str) -> RepoConfig:
        for repo in self.data["repos"]:
            if repo["src"] == src:
                return cast(RepoConfig, repo)
        assert False, "repo '%s' not found in manifest" % src

    def configure_repo(self, src: str, key: str, value: Any) -> None:
        repo = self.get_repo(src)
        repo[key] = value
        message = "Change %s %s: %s" % (src, key, value)
        self.push(message)

    def set_repo_url(self, src: str, url: str) -> None:
        self.configure_repo(src, "url", url)

    def set_repo_branch(self, src: str, branch: str) -> None:
        self.configure_repo(src, "branch", branch)

    def set_repo_sha1(self, src: str, ref: str) -> None:
        self.configure_repo(src, "sha1", ref)

    def set_repo_tag(self, src: str, tag: str) -> None:
        self.configure_repo(src, "tag", tag)

    def set_repo_file_copies(self, src: str, copies: List[CopyConfig]) -> None:
        copy_dicts = list()
        for copy_src, copy_dest in copies:
            copy_dicts.append({"src": copy_src, "dest": copy_dest})
        self.configure_repo(src, "copy", copy_dicts)

    def set_repo_remotes(self, src: str, remotes: List[RemoteConfig]) -> None:
        remote_dicts = list()
        for name, url in remotes:
            remote_dicts.append({"name": name, "url": url})
        repo = self.get_repo(src)
        repo["remotes"] = remote_dicts
        del repo["url"]
        message = "%s: remotes: %s" % (src, remote_dicts)
        self.push(message)

    def push(self, message: str) -> None:
        to_write = ruamel.yaml.dump(self.data)
        self.yaml_path.write_text(to_write)
        tsrc.git.run(self.path, "add", "manifest.yml")
        tsrc.git.run(self.path, "commit", "--message", message)
        current_branch = tsrc.git.get_current_branch(self.path)
        tsrc.git.run(self.path, "push", "origin", "--set-upstream", current_branch)

    def change_branch(self, branch: str) -> None:
        tsrc.git.run(self.path, "checkout", "-B", branch)
        tsrc.git.run(
            self.path,
            "push", "--no-verify", "origin",
            "--set-upstream", branch
        )


class GitServer():
    def __init__(self, tmpdir: Path) -> None:
        self.tmpdir = tmpdir
        self.bare_path = tmpdir / "srv"
        self.src_path = tmpdir / "src"
        self.add_repo("manifest", add_to_manifest=False)
        self.manifest = ManifestHandler(self.get_path("manifest"))
        self.manifest.init()
        self.manifest_url = self.get_url("manifest")

    def get_path(self, name: str) -> Path:
        return self.src_path / name

    def get_url(self, name: str) -> str:
        return str("file://" + (self.bare_path / name))

    def _create_repo(self, name: str, empty: bool = False, branch: str = "master") -> str:
        bare_path = self.bare_path / name
        bare_path.makedirs_p()
        tsrc.git.run(bare_path, "init", "--bare")
        src_path = self.get_path(name)
        src_path.makedirs_p()
        tsrc.git.run(src_path, "init")
        tsrc.git.run(src_path, "remote", "add", "origin", bare_path)
        tsrc.git.run(bare_path, "symbolic-ref", "HEAD", "refs/heads/%s" % branch)
        (src_path / "README").touch()
        tsrc.git.run(src_path, "add", "README")
        tsrc.git.run(src_path, "commit", "--message", "Initial commit")
        if branch != "master":
            tsrc.git.run(src_path, "checkout", "-b", branch)
        if not empty:
            tsrc.git.run(src_path, "push", "origin", "%s:%s" % (branch, branch))
        return str(bare_path)

    def add_repo(self, name: str,
                 add_to_manifest: bool = True, empty: bool = False,
                 default_branch: str = "master") -> str:
        self._create_repo(name, empty=empty, branch=default_branch)
        url = self.get_url(name)
        if add_to_manifest:
            self.manifest.add_repo(name, url, branch=default_branch)
        return url

    def add_group(self, group_name: str, repos: List[str]) -> None:
        for repo in repos:
            self.add_repo(repo)
        self.manifest.configure_group(group_name, repos)

    def push_file(self, name: str, file_path: str, *,
                  contents: str = "", message: str = "") -> None:
        src_path = self.get_path(name)
        full_path = src_path / file_path
        full_path.parent.makedirs_p()
        full_path.touch()
        if contents:
            full_path.write_text(contents)
        commit_message = message or ("Create/Update %s" % file_path)
        tsrc.git.run(src_path, "add", file_path)
        tsrc.git.run(src_path, "commit", "--message", commit_message)
        current_branch = tsrc.git.get_current_branch(src_path)
        tsrc.git.run(
            src_path,
            "push", "origin", "--set-upstream",
            current_branch
        )

    def tag(self, name: str, tag_name: str) -> None:
        src_path = self.get_path(name)
        tsrc.git.run(src_path, "tag", tag_name)
        tsrc.git.run(src_path, "push", "--no-verify", "origin", tag_name)

    def get_tags(self, name: str) -> List[str]:
        src_path = self.get_path(name)
        _, out = tsrc.git.run_captured(src_path, "tag")
        return out.splitlines()

    def get_branches(self, name: str) -> List[str]:
        src_path = self.get_path(name)
        _, out = tsrc.git.run_captured(src_path, "branch", "--list")
        return [x[2:].strip() for x in out.splitlines()]

    def get_sha1(self, name: str) -> str:
        src_path = self.get_path(name)
        _, out = tsrc.git.run_captured(src_path, "rev-parse", "HEAD")
        return out

    def change_repo_branch(self, name: str, new_branch: str) -> None:
        src_path = self.get_path(name)
        tsrc.git.run(src_path, "checkout", "-B", new_branch)
        tsrc.git.run(
            src_path,
            "push", "--no-verify", "origin",
            "--set-upstream",
            new_branch
        )

    def delete_branch(self, name: str, branch: str) -> None:
        src_path = self.get_path(name)
        tsrc.git.run(src_path, "push", "origin", "--delete", branch)


@pytest.fixture
def git_server(tmp_path: Path) -> GitServer:
    return GitServer(tmp_path)
