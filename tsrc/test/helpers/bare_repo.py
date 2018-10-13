from typing import List
from path import Path
import pygit2


class BareRepo:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.repo = pygit2.Repository(str(path))
        self.author = pygit2.Signature("tsrc", "tsrc")
        self.commiter = self.author

    def make_initial_commit(self) -> None:
        blob = self.repo.create_blob("This is the readme\n")
        tree_builder = self.repo.TreeBuilder()
        tree_builder.insert("README", blob, pygit2.GIT_FILEMODE_BLOB)
        tree = tree_builder.write()
        self.repo.create_commit("HEAD", self.author, self.commiter, "initial commit", tree, [])

    @classmethod
    def create(cls, path: Path, branch: str = "master", empty: bool = False) -> 'BareRepo':
        """ Create a new, non-empty, bare_repo """
        pygit2.init_repository(str(path), bare=True, initial_head=branch)
        res = cls(path)
        if not empty:
            res.make_initial_commit()
        return res

    def latest_commit(self) -> pygit2.Commit:
        return self.repo.head.get_object()

    def ensure_file(self, name: str, *, contents: str = "",
                    branch: str = "master",
                    commit_message: str = "") -> None:
        assert "/" not in name, "can only create blobs, not trees"
        blob = self.repo.create_blob(contents)
        tree_builder = self.repo.TreeBuilder()
        tree_builder.insert(name, blob, pygit2.GIT_FILEMODE_BLOB)
        tree = tree_builder.write()
        commit_message = commit_message or "Create/update %s" % name
        self.repo.create_commit(
            "refs/heads/%s" % branch,
            self.author, self.commiter, commit_message,
            tree, [self.latest_commit().id]
        )

    def tag(self, tag_name: str) -> None:
        # Note: this is a lightweight tag, so we just need to create a ref:
        oid = self.repo.head.get_object().id
        ref_name = "refs/tags/" + tag_name
        self.repo.references.create(ref_name, oid)

    def get_sha1(self, branch: str) -> str:
        commit_obj = self.repo.branches.local.get(branch).get_object()
        return str(commit_obj.id)

    def tags(self) -> List[str]:
        res = list()
        for ref in self.repo.references.objects:
            name = ref.name
            prefix = "refs/tags/"
            if name.startswith(prefix):
                res.append(name[len(prefix):])
        return res

    def create_branch(self, branch_name: str) -> None:
        self.repo.create_branch(branch_name, self.latest_commit())

    def delete_branch(self, branch_name: str) -> None:
        self.repo.references.delete("refs/heads/" + branch_name)

    def branches(self) -> List[str]:
        res = list()
        for ref in self.repo.references.objects:
            name = ref.name
            prefix = "refs/heads/"
            if name.startswith(prefix):
                res.append(name[len(prefix):])
        return res

    @property
    def url(self) -> str:
        return str(self.path)
