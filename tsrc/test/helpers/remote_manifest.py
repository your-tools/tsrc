from typing import cast, Any, Dict, List, Tuple
import ruamel.yaml
from path import Path

from .bare_repo import BareRepo


RepoConfig = Dict[str, Any]
CopyConfig = Tuple[str, str]
RemoteConfig = Tuple[str, str]


class RemoteManifest():
    """ Represent a bare git repo containing a manifest """

    def __init__(self, bare_repo: BareRepo) -> None:
        """ Init a new ManifestHandler. Note that path must
        be a git working copy, with a remote named 'origin'
        configured, so that changes made in the manifest
        can be published there

        """
        self.repo = bare_repo
        self.data = {"repos": list()}  # type: Dict[str, Any]
        self.url = bare_repo.url
        self.branch = "master"

    @classmethod
    def create(cls, path: Path) -> "RemoteManifest":
        bare_repo = BareRepo.create(path)
        res = cls(bare_repo)
        res.init()
        return res

    def init(self) -> None:
        self.write_self(message="Add an empty manifest")

    def add_repo(self, src: str, url: str, branch: str = "master") -> None:
        repo_config = ({"url": str(url), "src": src})
        if branch != "master":
            repo_config["branch"] = branch
        self.data["repos"].append(repo_config)
        self.write_self(message="add %s")

    def configure_group(self, name: str, repos: List[str]) -> None:
        groups = self.data.get("groups")
        if not groups:
            self.data["groups"] = dict()
            groups = self.data["groups"]
        groups[name] = dict()
        groups[name]["repos"] = repos
        self.write_self(message="add %s group" % name)

    def configure_gitlab(self, *, url: str) -> None:
        self.data["gitlab"] = dict()
        self.data["gitlab"]["url"] = url
        self.write_self("Add gitlab URL: %s" % url)

    def get_repo(self, src: str) -> RepoConfig:
        for repo in self.data["repos"]:
            if repo["src"] == src:
                return cast(RepoConfig, repo)
        assert False, "repo '%s' not found in manifest" % src

    def configure_repo(self, src: str, key: str, value: Any) -> None:
        repo = self.get_repo(src)
        repo[key] = value
        message = "Change %s %s: %s" % (src, key, value)
        self.write_self(message)

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
        self.write_self(message)

    def write_self(self, message: str) -> None:
        manifest_contents = ruamel.yaml.dump(self.data)
        self.repo.ensure_file(
            "manifest.yml",
            contents=manifest_contents,
            commit_message=message,
            branch=self.branch
        )

    def change_branch(self, branch: str) -> None:
        self.branch = branch
