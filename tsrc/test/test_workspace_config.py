from pathlib import Path

from tsrc.workspace.config import WorkspaceConfig


def test_save(tmp_path: Path) -> None:
    """Check that workspace config can be written
    and read.

    Note: the writing is done by `tsrc init`, all other
    commands simply read the file.
    """
    config = WorkspaceConfig(
        manifest_url="https://gitlab.example",
        manifest_branch="stable",
        shallow_clones=True,
        repo_groups=["default", "a-team"],
        clone_all_repos=False,
        singular_remote=None,
    )
    persistent_path = tmp_path / "config.yml"
    config.save_to_file(persistent_path)
    actual = WorkspaceConfig.from_file(persistent_path)
    assert actual == config
