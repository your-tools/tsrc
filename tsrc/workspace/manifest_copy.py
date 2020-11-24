from pathlib import Path

import tsrc.manifest
from tsrc.workspace.local_manifest import LocalManifest


class ManifestCopy(LocalManifest):
    def __init__(self, manifest_copy_path: Path):
        self.manifest_copy_path = manifest_copy_path

    def update(self) -> None:
        pass

    def get_manifest(self) -> tsrc.manifest.Manifest:
        return tsrc.manifest.load(self.manifest_copy_path)
