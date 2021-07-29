""" The GitServer class can create bare git repositories and a manifest
that contains valid git URLs.

It is mostly used by the end-to-end tests in tsrc/test/cli/.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

import pygit2
import pytest
import ruamel.yaml

RepoConfig = Dict[str, Any]
CopyConfig = Tuple[str, str]
RemoteConfig = Tuple[str, str]


class BaseTestRepo:
    user = pygit2.Signature("Tasty Test", "test@tsrc.io")

    def __init__(self, repo: pygit2.Repository, path: Path) -> None:
        self._repo = repo
        self.path = path


class BareRepo(BaseTestRepo):
    @classmethod
    def create(cls, path: Path, initial_branch: str, empty: bool = False) -> "BareRepo":
        repo = pygit2.init_repository(str(path), bare=True, initial_head=initial_branch)
        if empty:
            return cls(repo, path)

        blob_oid = repo.create_blob(b"this is the readme")
        tree_builder = repo.TreeBuilder()
        tree_builder.insert("README", blob_oid, pygit2.GIT_FILEMODE_BLOB)

        repo.create_commit(
            "HEAD", cls.user, cls.user, "initial commit", tree_builder.write(), []
        )
        return cls(repo, path)

    @classmethod
    def open(cls, path: Path) -> "BareRepo":
        repo = pygit2.Repository(path)
        assert repo.is_bare
        return cls(repo, path)

    def create_tag(self, tag_name: str, *, branch: str, force: bool = False) -> None:
        ref_name = "refs/heads/" + branch
        ref = self._repo.references.get(ref_name)
        assert ref
        tag_ref = "refs/tags/" + tag_name
        self._repo.create_reference(tag_ref, ref.target, force=force)

    def ensure_ref(self, name: str) -> pygit2.Reference:
        ref = self._repo.references.get(name)
        if not ref:
            ref = self._repo.create_reference(name, self._repo.head.target)
        return ref

    def commit_file(
        self,
        name: str,
        *,
        branch: str,
        contents: str,
        message: str,
        mode: int = pygit2.GIT_FILEMODE_BLOB,
    ) -> pygit2.Tree:
        assert "/" not in name, "creating subtrees is not supported"

        ref_name = "refs/heads/" + branch
        ref = self.ensure_ref(ref_name)
        last_commit = self._repo.get(ref.target)
        parents = [last_commit.oid]

        old_tree = last_commit.tree
        tree_builder = self._repo.TreeBuilder(old_tree)
        blob_oid = self._repo.create_blob(contents.encode())
        tree_builder.insert(name, blob_oid, mode)
        new_tree = tree_builder.write()

        author = self.user
        committer = self.user
        self._repo.create_commit(
            ref_name, author, committer, message, new_tree, parents
        )

    def get_sha1(self) -> str:
        return self._repo.head.target.hex  # type: ignore


class TestRepo(BaseTestRepo):
    @classmethod
    def clone(
        cls, url: str, path: Path, *, initial_branch: str = "master"
    ) -> "TestRepo":
        repo = pygit2.clone_repository(url, str(path), checkout_branch=initial_branch)
        return cls(repo, path)

    @classmethod
    def open(cls, path: Path) -> "TestRepo":
        repo = pygit2.Repository(path)
        assert not repo.is_bare
        return cls(repo, path)

    def add_submodule(self, *, path: Path, url: str) -> None:
        self._repo.add_submodule(url, str(path))

    def commit_all_and_push(self, *, message: str) -> None:
        ref = self._repo.references.get("refs/heads/master")
        last_commit = self._repo.get(ref.target)
        parents = [last_commit.oid]
        self._repo.index.add_all()
        tree = self._repo.index.write_tree()
        self._repo.create_commit(
            "HEAD",
            self.user,
            self.user,
            message,
            tree,
            parents,
        )
        origin = self._repo.remotes["origin"]
        origin.push(["refs/heads/master"])

    def fetch_and_reset(
        self,
        *,
        local_branch: str = "master",
        remote_name: str = "origin",
        remote_branch: str = "master",
    ) -> None:
        """Fetch and reset the current branch using remote_branch of the given remote"""
        origin = self._repo.remotes[remote_name]
        origin.fetch([f"refs/heads/{remote_branch}"], prune=pygit2.GIT_FETCH_PRUNE)
        remote_target = self._repo.lookup_reference(
            f"refs/remotes/{remote_name}/{remote_branch}"
        ).target
        current_ref = self._repo.lookup_reference(f"refs/heads/{local_branch}")
        current_ref.set_target(remote_target)
        self._repo.reset(current_ref.target, pygit2.GIT_RESET_HARD)


class ManifestHandler:
    """Contains methods to update repositories configuration
    in the manifest repo.

    Data is written directly to the underlying bare repo instance,
    using `refs/heads/master` ref by default.

    After a call `change_branch(new_branch)`, changes will be
    written to refs/heads/new_branch` instead.
    """

    def __init__(self, repo: BareRepo) -> None:

        self.repo = repo
        self.data: Dict[str, Any] = {"repos": []}
        self.branch = "master"
        self.write_changes("Add an empty manifest")

    def change_branch(self, new_branch: str) -> None:
        self.repo.ensure_ref("refs/heads/" + new_branch)
        self.branch = new_branch

    def write_changes(self, message: str) -> None:
        to_write = ruamel.yaml.dump(self.data)
        assert to_write
        self.repo.commit_file(
            "manifest.yml", contents=to_write, message=message, branch=self.branch
        )

    def add_repo(self, name: str, url: str, branch: str = "master") -> None:
        repo_config = {"url": str(url), "dest": name}
        if branch != "master":
            repo_config["branch"] = branch
        self.data["repos"].append(repo_config)
        self.write_changes(message=f"add {name}")

    def configure_group(
        self, name: str, repos: List[str], includes: Optional[List[str]] = None
    ) -> None:
        groups = self.data.get("groups")
        if not groups:
            self.data["groups"] = {}
            groups = self.data["groups"]
        groups[name] = {}
        groups[name]["repos"] = repos
        if includes:
            groups[name]["includes"] = includes
        self.write_changes(message=f"add/update {name} group")

    def get_repo(self, name: str) -> RepoConfig:
        for repo in self.data["repos"]:
            if repo["dest"] == name:
                return cast(RepoConfig, repo)
        raise AssertionError(f"repo '{name}' not found in manifest")

    def configure_repo(self, name: str, key: str, value: Any) -> None:
        repo = self.get_repo(name)
        repo[key] = value
        message = f"Change {name} {key}: {value}"
        self.write_changes(message)

    def set_repo_url(self, name: str, url: str) -> None:
        self.configure_repo(name, "url", url)

    def set_repo_branch(self, name: str, branch: str) -> None:
        self.configure_repo(name, "branch", branch)

    def set_repo_sha1(self, name: str, ref: str) -> None:
        self.configure_repo(name, "sha1", ref)

    def set_repo_tag(self, name: str, tag: str) -> None:
        self.configure_repo(name, "tag", tag)

    def set_file_copy(self, repo_name: str, src: str, dest: str) -> None:
        copies = [{"file": src, "dest": dest}]
        self.configure_repo(repo_name, "copy", copies)

    def set_symlink(self, repo_name: str, source: str, target: str) -> None:
        symlinks = [{"source": source, "target": target}]
        self.configure_repo(repo_name, "symlink", symlinks)

    def set_repo_remotes(self, name: str, remotes: List[RemoteConfig]) -> None:
        remote_dicts = []
        for remote_name, remote_url in remotes:
            remote_dicts.append({"name": remote_name, "url": remote_url})
        repo = self.get_repo(name)
        repo["remotes"] = remote_dicts
        del repo["url"]
        message = f"{name}: remotes: {remote_dicts}"
        self.write_changes(message)


class GitServer:
    """
    Holds a collection of git repositories in `self.bare_path, itself a
    subdirectory of `tmpdir`.

    Also uses a ManifestHandler instance to update the manifest
    configuration, like adding a new repo.
    """

    def __init__(self, tmpdir: Path) -> None:
        srv_path = tmpdir / "srv"
        srv_path.mkdir()
        self.bare_path = srv_path / "bare"
        self.src_path = srv_path / "src"
        self.bare_path.mkdir()
        self.src_path.mkdir()
        self.manifest_url = self.get_url("manifest")

        manifest_repo = self._create_repo("manifest")
        self.manifest = ManifestHandler(manifest_repo)

    def get_url(self, name: str) -> str:
        return f"file://{self.bare_path / name}"

    def url_to_local_path(self, url: str) -> str:
        """It seems that libgit2 not support file:// local URLs like git does
        so we use this conversion method when using PyGit2 when cloning or
        handling submodules
        """
        return url.replace("file://", "")

    def _get_repo(self, name: str) -> BareRepo:
        repo_path = self.bare_path / name
        return BareRepo.open(repo_path)

    def _create_repo(
        self, name: str, empty: bool = False, branch: str = "master"
    ) -> BareRepo:
        repo_path = self.bare_path / name
        assert (
            not repo_path.exists()
        ), f"cannot create repo in {repo_path}: this folder already exits"
        repo_path.mkdir(parents=True, exist_ok=True)
        repo = BareRepo.create(repo_path, initial_branch=branch, empty=empty)
        return repo

    def add_submodule(self, name: str, *, path: Path, url: str) -> None:
        # pygit2 does not know how to add a submodule in a bare repo, so we have
        # to do it with a non-bare repo.
        bare_path = self.bare_path / name
        src_path = self.src_path / name
        test_repo = TestRepo.clone(str(bare_path), src_path)

        test_repo.add_submodule(path=path, url=self.url_to_local_path(url))
        test_repo.commit_all_and_push(message=f"Add submodule in {path}")

    def update_submodule(self, name: str, path: str) -> None:
        parent_path = self.src_path / name
        sub_path = parent_path / path

        # Fetch and reset the submodule
        sub_repo = TestRepo.open(sub_path)
        sub_repo.fetch_and_reset()

        # Make a commit which updates the submodule in the
        # parent repo and push it
        parent_repo = TestRepo.open(parent_path)
        parent_repo.commit_all_and_push(message=f"Update submodule in {path}")

    def add_repo(
        self,
        name: str,
        empty: bool = False,
        default_branch: str = "master",
        add_to_manifest: bool = True,
    ) -> str:
        self._create_repo(name, empty=empty, branch=default_branch)
        url = self.get_url(name)
        if add_to_manifest:
            self.manifest.add_repo(name, url, branch=default_branch)
        return url

    def add_group(self, group_name: str, repos: List[str]) -> None:
        for repo in repos:
            self.add_repo(repo)
        self.manifest.configure_group(group_name, repos)

    def push_file(
        self,
        name: str,
        file_path: str,
        *,
        contents: str = "",
        message: str = "",
        branch: str = "master",
        executable: bool = False,
    ) -> None:
        if executable:
            file_mode = pygit2.GIT_FILEMODE_BLOB_EXECUTABLE
        else:
            file_mode = pygit2.GIT_FILEMODE_BLOB
        repo = self._get_repo(name)
        if not message:
            message = "add/update " + file_path
        repo.commit_file(
            file_path, contents=contents, message=message, branch=branch, mode=file_mode
        )

    def tag(
        self, name: str, tag_name: str, *, branch: str = "master", force: bool = False
    ) -> None:
        repo = self._get_repo(name)
        repo.create_tag(tag_name, branch=branch, force=force)

    def get_sha1(self, name: str) -> str:
        repo = self._get_repo(name)
        return repo.get_sha1()


@pytest.fixture
def git_server(tmp_path: Path) -> GitServer:
    return GitServer(tmp_path)
