import shutil
from pathlib import Path

import ruamel.yaml

from tsrc.test.helpers.cli import CLI
from tsrc.test.helpers.git_server import GitServer


def test_apply_manifest_adds_new_repo(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    """Scenario:

    * Create a manifest with one repo
    * Create a workspace using `tsrc init`
    * Copy the manifest file somewhere in the workspace
    * Create a new repo on the server
    * Edit the copied manifest to contain the new repo, including
      a file system copy
    * Run `tsrc apply-manifest /path/to/copied_manifest`
    * Check that the new repo is cloned
    * Check that the copy is performed

    """
    git_server.add_repo("foo")
    tsrc_cli.run("init", git_server.manifest_url)

    cloned_manifest_path = workspace_path / ".tsrc/manifest/manifest.yml"
    copied_manifest_path = workspace_path / "manifest.yml"
    shutil.copy(cloned_manifest_path, copied_manifest_path)

    bar_url = git_server.add_repo("bar", add_to_manifest=False)
    git_server.push_file("bar", "src")
    add_repo_to_manifest_with_copy(copied_manifest_path, "bar", bar_url)

    tsrc_cli.run("apply-manifest", str(copied_manifest_path))

    assert (workspace_path / "bar").exists(), "bar repo should have been cloned"
    assert (
        workspace_path / "dest"
    ).exists(), "file system operations should have been performed"


def add_repo_to_manifest_with_copy(manifest_path: Path, dest: str, url: str) -> None:
    yaml = ruamel.yaml.YAML()
    data = yaml.load(manifest_path.read_text())
    repos = data["repos"]
    to_add = {"dest": dest, "url": url, "copy": [{"file": "src", "dest": "dest"}]}
    repos.append(to_add)
    with manifest_path.open("w") as fileobj:
        yaml.dump(data, fileobj)
