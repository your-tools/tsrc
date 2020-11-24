from pathlib import Path

import tsrc.manifest
from tsrc.workspace.local_manifest import LocalManifest


class ClonedManifest(LocalManifest):
    """Represent a manifest repository that has been cloned locally
    inside `<workspace>/.tsrc/manifest`.

    Usage:

    >>> cloned_manifest = ClonedManifest(workspace / ".tsrc/manifest"),
            url="git@acme.com/manifest.git", branch="devel"
         )

    # First, update the cloned repository using the remote git URL and the
    # branch passed in the constructor
    >> cloned_manifest.update()

    # Then, read the `manifest.yml` file from the clone repository:
    >>> manifest = cloned_manifest.get_manifest()

    """

    def __init__(self, clone_path: Path, *, url: str, branch: str) -> None:
        self.clone_path = clone_path
        self.url = url
        self.branch = branch

    def update(self) -> None:
        if self.clone_path.exists():
            self._reset_manifest_clone()
        else:
            self._clone_manifest()

    def get_manifest(self) -> tsrc.manifest.Manifest:
        return tsrc.manifest.load(self.clone_path / "manifest.yml")

    def _reset_manifest_clone(self) -> None:
        tsrc.git.run(self.clone_path, "remote", "set-url", "origin", self.url)

        tsrc.git.run(self.clone_path, "fetch")
        tsrc.git.run(self.clone_path, "checkout", "-B", self.branch)
        # fmt: off
        tsrc.git.run(
            self.clone_path, "branch", self.branch,
            "--set-upstream-to", f"origin/{self.branch}"
        )
        # fmt: on
        ref = f"origin/{self.branch}"
        tsrc.git.run(self.clone_path, "reset", "--hard", ref)

    def _clone_manifest(self) -> None:
        parent = self.clone_path.parent
        name = self.clone_path.name
        parent.mkdir(parents=True, exist_ok=True)
        tsrc.git.run(
            self.clone_path.parent, "clone", self.url, "--branch", self.branch, name
        )
