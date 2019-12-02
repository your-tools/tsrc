from typing import cast, Optional, List, Tuple  # noqa
from path import Path

import tsrc
import tsrc.manifest


class LocalManifest:
    """ Represent a manifest that has been cloned locally inside the
    hidden <workspace>/.tsrc/manifest

    """

    def __init__(self, clone_path: Path) -> None:
        self.clone_path = clone_path

    def update(self, url: str, *, branch: str) -> None:
        if self.clone_path.exists():
            self._reset_manifest_clone(url, branch=branch)
        else:
            self._clone_manifest(url, branch=branch)

    def get_manifest(self) -> tsrc.manifest.Manifest:
        return tsrc.manifest.load(self.clone_path / "manifest.yml")

    def _reset_manifest_clone(self, url: str, *, branch: str) -> None:
        tsrc.git.run(self.clone_path, "remote", "set-url", "origin", url)

        tsrc.git.run(self.clone_path, "fetch")
        tsrc.git.run(self.clone_path, "checkout", "-B", branch)
        # fmt: off
        tsrc.git.run(
            self.clone_path, "branch", branch,
            "--set-upstream-to", "origin/%s" % branch
        )
        # fmt: on
        ref = "origin/%s" % branch
        tsrc.git.run(self.clone_path, "reset", "--hard", ref)

    def _clone_manifest(self, url: str, *, branch: str) -> None:
        parent, name = self.clone_path.splitpath()
        parent.makedirs_p()
        tsrc.git.run(self.clone_path.parent, "clone", url, "--branch", branch, name)
