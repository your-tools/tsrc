from typing import cast, Any, Dict, List, Tuple
import ruamel.yaml

import tsrc
import tsrc.git

from path import Path

RepoConfig = Dict[str, Any]
CopyConfig = Tuple[str, str]
RemoteConfig = Tuple[str, str]


class ManifestHandler():
    """ Represent a local copy of a manifest. """

    def __init__(self, path: Path) -> None:
        """ Init a new ManifestHandler. Note that path must
        be a git working copy, with a remote named 'origin'
        configured, so that changes made in the manifest
        can be published there

        """
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
