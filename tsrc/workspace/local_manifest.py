from pathlib import Path

from tsrc.git import run_git
from tsrc.manifest import Manifest, load_manifest


class LocalManifest:
    """Represent a manifest repository that has been cloned locally
    inside `<workspace>/.tsrc/manifest`.

    Usage:

    >>> local_manifest = LocalManifest(Path(workspace / ".tsrc/manifest")

    # First, update the cloned repository using a remote git URL and a
    # branch:
    >>> manifest.update("git@acme.com/manifest.git", branch="devel")

    # Then, read the `manifest.yml` file from the clone repository:
    >>> manifest = local_manifest.get_manifest()

    """

    def __init__(self, clone_path: Path) -> None:
        self.clone_path = clone_path

    def update(self, url: str, *, branch: str) -> None:
        if self.clone_path.exists():
            self._reset_manifest_clone(url, branch=branch)
        else:
            self._clone_manifest(url, branch=branch)

    def get_manifest(self) -> Manifest:
        return load_manifest(self.clone_path / "manifest.yml")

    def _reset_manifest_clone(self, url: str, *, branch: str) -> None:
        run_git(self.clone_path, "remote", "set-url", "origin", url)
        run_git(self.clone_path, "fetch")
        run_git(self.clone_path, "checkout", "-B", branch)
        run_git(
            self.clone_path, "branch", branch, "--set-upstream-to", f"origin/{branch}"
        )
        ref = f"origin/{branch}"
        run_git(self.clone_path, "reset", "--hard", ref)

    def _clone_manifest(self, url: str, *, branch: str) -> None:
        parent = self.clone_path.parent
        name = self.clone_path.name
        parent.mkdir(parents=True, exist_ok=True)
        run_git(self.clone_path.parent, "clone", url, "--branch", branch, name)
