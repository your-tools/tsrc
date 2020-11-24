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
    * Edit the copied manifest to contain the new repo
    * Run `tsrc apply-manifest /path/to/copied_manifest`
    * Check that the new repo gets cloned

    """
    git_server.add_repo("foo")
    tsrc_cli.run("init", git_server.manifest_url)

    cloned_manifest_path = workspace_path / ".tsrc/manifest/manifest.yml"
    copied_manifest_path = workspace_path / "manifest.yml"
    shutil.copy(cloned_manifest_path, copied_manifest_path)

    bar_url = git_server.add_repo("bar", add_to_manifest=False)
    add_repo_to_manifest(copied_manifest_path, "bar", bar_url)

    tsrc_cli.run("apply-manifest", str(copied_manifest_path))

    assert (workspace_path / "bar").exists(), "bar repo should have been cloned"


def test_apply_manifest_performs_filesystem_operation(
    tsrc_cli: CLI, git_server: GitServer, workspace_path: Path
) -> None:
    """Scenario:

    * Create a manifest with one repo
    * Create a workspace using `tsrc init`
    * Copy the manifest file somewhere in the workspace
    * Edit the copied manifest to contain a new symlink
    * Run `tsrc apply-manifest /path/to/copied_manifest`
    * Check that the new symlink gets created

    """
    git_server.add_repo("foo")
    tsrc_cli.run("init", git_server.manifest_url)

    cloned_manifest_path = workspace_path / ".tsrc/manifest/manifest.yml"
    copied_manifest_path = workspace_path / "manifest.yml"
    shutil.copy(cloned_manifest_path, copied_manifest_path)

    add_symlink_to_manifest(
        copied_manifest_path, "foo", source="some_source", target="foo/README"
    )
    tsrc_cli.run("apply-manifest", str(copied_manifest_path))

    assert (
        workspace_path / "some_source"
    ).exists(), "some_source symlink should have been created"


def add_repo_to_manifest(manifest_path: Path, dest: str, url: str) -> None:
    yaml = ruamel.yaml.YAML()
    data = yaml.load(manifest_path.read_text())
    repos = data["repos"]
    to_add = {"dest": dest, "url": url}
    repos.append(to_add)
    with manifest_path.open("w") as fileobj:
        yaml.dump(data, fileobj)


def add_symlink_to_manifest(
    manifest_path: Path, dest: str, *, source: str, target: str
) -> None:
    yaml = ruamel.yaml.YAML()
    data = yaml.load(manifest_path.read_text())
    repos = data["repos"]
    (repo_config,) = [x for x in repos if x["dest"] == dest]
    repo_config["symlink"] = [{"source": source, "target": target}]
    with manifest_path.open("w") as fileobj:
        yaml.dump(data, fileobj)
