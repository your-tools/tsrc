from typing import cast, Any, Dict, List, Tuple
import ruamel.yaml
import pytest

from path import Path
import pygit2

RepoConfig = Dict[str, Any]
CopyConfig = Tuple[str, str]
RemoteConfig = Tuple[str, str]


class TestRepo:
    user = pygit2.Signature("Tasty Test", "test@tsrc.io")

    def __init__(self, path: Path) -> None:
        self._repo = pygit2.Repository(str(path))

    @classmethod
    def create_bare(
        cls, path: Path, initial_branch: str, empty: bool = False
    ) -> "TestRepo":
        repo = pygit2.init_repository(str(path), bare=True, initial_head=initial_branch)
        if empty:
            return cls(path)

        blob_oid = repo.create_blob(b"this is the readme")
        tree_builder = repo.TreeBuilder()
        tree_builder.insert("README", blob_oid, pygit2.GIT_FILEMODE_BLOB)

        repo.create_commit(
            "HEAD", cls.user, cls.user, "initial commit", tree_builder.write(), []
        )
        return cls(path)

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
        mode: int = pygit2.GIT_FILEMODE_BLOB
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
        commiter = self.user
        self._repo.create_commit(ref_name, author, commiter, message, new_tree, parents)

    def get_sha1(self) -> str:
        return self._repo.head.target.hex  # type: ignore


class ManifestHandler:
    def __init__(self, repo: TestRepo) -> None:
        self.repo = repo
        self.data = {"repos": []}  # type: Dict[str, Any]
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

    def add_repo(self, dest: str, url: str, branch: str = "master") -> None:
        repo_config = {"url": str(url), "dest": dest}
        if branch != "master":
            repo_config["branch"] = branch
        self.data["repos"].append(repo_config)
        self.write_changes(message="add %s" % dest)

    def configure_group(self, name: str, repos: List[str]) -> None:
        groups = self.data.get("groups")
        if not groups:
            self.data["groups"] = {}
            groups = self.data["groups"]
        groups[name] = {}
        groups[name]["repos"] = repos
        self.write_changes(message="add %s group" % name)

    def get_repo(self, dest: str) -> RepoConfig:
        for repo in self.data["repos"]:
            if repo["dest"] == dest:
                return cast(RepoConfig, repo)
        assert False, "repo '%s' not found in manifest" % dest

    def configure_repo(self, dest: str, key: str, value: Any) -> None:
        repo = self.get_repo(dest)
        repo[key] = value
        message = "Change %s %s: %s" % (dest, key, value)
        self.write_changes(message)

    def set_repo_url(self, dest: str, url: str) -> None:
        self.configure_repo(dest, "url", url)

    def set_repo_branch(self, dest: str, branch: str) -> None:
        self.configure_repo(dest, "branch", branch)

    def set_repo_sha1(self, dest: str, ref: str) -> None:
        self.configure_repo(dest, "sha1", ref)

    def set_repo_tag(self, dest: str, tag: str) -> None:
        self.configure_repo(dest, "tag", tag)

    def set_repo_file_copies(self, dest: str, copies: List[CopyConfig]) -> None:
        copy_dicts = []
        for copy_src, copy_dest in copies:
            copy_dicts.append({"file": copy_src, "dest": copy_dest})
        self.configure_repo(dest, "copy", copy_dicts)

    def set_repo_remotes(self, dest: str, remotes: List[RemoteConfig]) -> None:
        remote_dicts = []
        for name, url in remotes:
            remote_dicts.append({"name": name, "url": url})
        repo = self.get_repo(dest)
        repo["remotes"] = remote_dicts
        del repo["url"]
        message = "%s: remotes: %s" % (dest, remote_dicts)
        self.write_changes(message)


class GitServer:
    def __init__(self, tmpdir: Path) -> None:
        self.tmpdir = tmpdir
        self.bare_path = tmpdir / "srv"
        self.manifest_url = self.get_url("manifest")

        manifest_repo = self._create_repo("manifest")
        self.manifest = ManifestHandler(manifest_repo)

    def get_url(self, name: str) -> str:
        return str("file://" + (self.bare_path / name))

    def _get_repo(self, name: str) -> TestRepo:
        repo_path = self.bare_path / name
        return TestRepo(repo_path)

    def _create_repo(
        self, name: str, empty: bool = False, branch: str = "master"
    ) -> TestRepo:
        repo_path = self.bare_path / name
        repo_path.makedirs_p()
        repo = TestRepo.create_bare(repo_path, initial_branch=branch, empty=empty)
        return repo

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
        executable: bool = False
    ) -> None:
        if executable:
            file_mode = pygit2.GIT_FILEMODE_BLOB_EXECUTABLE
        else:
            file_mode = pygit2.GIT_FILEMODE_BLOB
        repo = self._get_repo(name)
        if not message:
            message = "add/update " + file_path
        repo.commit_file(
            file_path,
            contents=contents,
            message=message,
            branch=branch,
            mode=file_mode
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
