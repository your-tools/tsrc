import tsrc
from tsrc.workspace.manifest_config import ManifestConfig
from path import Path
import pytest


def test_it_must_have_file_xor_url() -> None:
    with pytest.raises(tsrc.Error):
        ManifestConfig.from_dict(
            {"url": "foo@bar.com", "file_path": Path("/path/to/yml")}
        )

    with pytest.raises(tsrc.Error):
        ManifestConfig.from_dict({})
