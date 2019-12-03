from tsrc.workspace.config import WorkspaceConfig
from path import Path


def test_can_roundtrip(tmp_path: Path) -> None:
    config = WorkspaceConfig(
        manifest_url="https://gitlab.example",
        manifest_branch="stable",
        shallow_clones=True,
        repo_groups=["default", "a-team"],
        clone_all_repos=False,
    )
    persistent_path = tmp_path / "config.yml"
    config.save_to_file(persistent_path)
    actual = WorkspaceConfig.from_file(persistent_path)
    assert actual == config
