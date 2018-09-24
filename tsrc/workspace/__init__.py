""" Implementation of the tsrc Workspace: a collection of git repositories
"""

import stat
import textwrap
from typing import cast, Iterable, List, Tuple, Dict, Any, Optional, NewType  # noqa

from path import Path
import ui

import tsrc
import tsrc.executor
import tsrc.git
import tsrc.manifest

from .manifest_config import ManifestConfig


class LocalManifest:
    """ Represent a manifest that has been cloned locally inside the
    hidden <workspace>/.tsrc directory, along with its configuration

    """
    def __init__(self, workspace_path: Path) -> None:
        hidden_path = workspace_path.joinpath(".tsrc")
        self.clone_path = hidden_path.joinpath("manifest")
        self.cfg_path = hidden_path.joinpath("manifest.yml")
        self.manifest = None  # type: Optional[tsrc.manifest.Manifest]

    @property
    def branch(self) -> str:
        return self.load_config().branch

    @property
    def shallow(self) -> bool:
        return self.load_config().shallow

    @property
    def copyfiles(self) -> List[Tuple[str, str]]:
        assert self.manifest, "manifest is empty. Did you call load()?"
        return self.manifest.copyfiles

    @property
    def active_groups(self) -> List[str]:
        return self.load_config().groups

    def get_repos(self) -> List[tsrc.Repo]:
        assert self.manifest, "manifest is empty. Did you call load()?"
        return self.manifest.get_repos(groups=self.active_groups)

    def load(self) -> None:
        yml_path = self.clone_path.joinpath("manifest.yml")
        if not yml_path.exists():
            message = "No manifest found in {}. Did you run `tsrc init` ?"
            raise tsrc.Error(message.format(yml_path))
        self.manifest = tsrc.manifest.load(yml_path)

    def get_gitlab_url(self) -> str:
        assert self.manifest, "manifest is empty. Did you call load()?"
        gitlab_config = self.manifest.gitlab
        if not gitlab_config:
            raise tsrc.Error("No gitlab configuration found in manifest")
        return cast(str, gitlab_config["url"])

    def get_url(self, src: str) -> str:
        assert self.manifest, "manifest is empty. Did you call load()?"
        return self.manifest.get_url(src)

    def configure(self, manifest_config: ManifestConfig) -> None:
        if not manifest_config.url:
            raise tsrc.Error("Manifest URL is required")
        self._ensure_git_state(manifest_config)
        self.save_config(manifest_config)

    def update(self) -> None:
        ui.info_2("Updating manifest")
        if not self.clone_path.exists():
            message = "Could not find manifest in {}. "
            message += "Did you run `tsrc init` ?"
            raise tsrc.Error(message.format(self.clone_path))
        cmd = ("fetch", "--prune", "origin")
        tsrc.git.run_git(self.clone_path, *cmd)
        cmd = ("reset", "--hard", "@{u}")
        tsrc.git.run_git(self.clone_path, *cmd)

    def save_config(self, config: ManifestConfig) -> None:
        config.save_to_file(self.cfg_path)

    def load_config(self) -> ManifestConfig:
        return ManifestConfig.from_file(self.cfg_path)

    def _ensure_git_state(self, config: ManifestConfig) -> None:
        if self.clone_path.exists():
            self._reset_manifest_clone(config)
        else:
            self._clone_manifest(config)

    def _reset_manifest_clone(self, config: ManifestConfig) -> None:
        tsrc.git.run_git(self.clone_path, "remote", "set-url", "origin", config.url)

        tsrc.git.run_git(self.clone_path, "fetch")
        tsrc.git.run_git(self.clone_path, "checkout", "-B", config.branch)
        tsrc.git.run_git(
            self.clone_path, "branch", config.branch,
            "--set-upstream-to", "origin/%s" % config.branch
        )
        if config.tag:
            ref = config.tag
        else:
            ref = "origin/%s" % config.branch
        tsrc.git.run_git(self.clone_path, "reset", "--hard", ref)

    def _clone_manifest(self, config: ManifestConfig) -> None:
        parent, name = self.clone_path.splitpath()
        parent.makedirs_p()
        ref = ""  # type: str
        if config.tag:
            ref = config.tag
        elif config.branch:
            ref = config.branch
        args = ["clone", config.url, name]
        if ref:
            args += ["--branch", ref]
        tsrc.git.run_git(self.clone_path.parent, *args)


class Workspace():
    def __init__(self, root_path: Path) -> None:
        self.root_path = root_path
        self.local_manifest = LocalManifest(root_path)

    def joinpath(self, *parts: str) -> Path:
        return self.root_path.joinpath(*parts)

    def get_repos(self) -> List[tsrc.Repo]:
        return self.local_manifest.get_repos()

    def load_manifest(self) -> None:
        self.local_manifest.load()

    def get_gitlab_url(self) -> str:
        return self.local_manifest.get_gitlab_url()

    def configure_manifest(self, manifest_config: ManifestConfig) -> None:
        self.local_manifest.configure(manifest_config)

    def update_manifest(self) -> None:
        self.local_manifest.update()

    @property
    def active_groups(self) -> List[str]:
        return self.local_manifest.active_groups

    @property
    def shallow(self) -> bool:
        return self.local_manifest.shallow

    def clone_missing(self) -> None:
        to_clone = list()
        for repo in self.get_repos():
            repo_path = self.joinpath(repo.src)
            if not repo_path.exists():
                to_clone.append(repo)
        cloner = Cloner(self)
        tsrc.executor.run_sequence(to_clone, cloner)

    def set_remotes(self) -> None:
        remote_setter = RemoteSetter(self)
        tsrc.executor.run_sequence(self.get_repos(), remote_setter)

    def copy_files(self) -> None:
        file_copier = FileCopier(self)
        tsrc.executor.run_sequence(self.local_manifest.copyfiles, file_copier)

    def sync(self) -> None:
        syncer = Syncer(self)
        try:
            tsrc.executor.run_sequence(self.get_repos(), syncer)
        finally:
            syncer.display_bad_branches()

    def enumerate_repos(self) -> Iterable[Tuple[int, tsrc.Repo, Path]]:
        """ Yield (index, repo, full_path) for all the repos """
        for i, repo in enumerate(self.get_repos()):
            full_path = self.joinpath(repo.src)
            yield (i, repo, full_path)

    def get_url(self, src: str) -> str:
        """ Return the url of the project in `src` """
        return self.local_manifest.get_url(src)


class Cloner(tsrc.executor.Task[tsrc.Repo]):
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def description(self) -> str:
        return "Cloning missing repos"

    def display_item(self, repo: tsrc.Repo) -> str:
        return repo.src

    def check_shallow_with_sha1(self, repo: tsrc.Repo) -> None:
        if not repo.sha1:
            return
        if self.workspace.shallow:
            message = textwrap.dedent(
                "Cannot use --shallow with a fixed sha1 ({repo.sha1})\n"
                "Consider using a tag instead"
            )
            message = message.format(repo=repo)
            ui.fatal(message)

    def clone_repo(self, repo: tsrc.Repo) -> None:
        repo_path = self.workspace.joinpath(repo.src)
        parent, name = repo_path.splitpath()
        parent.makedirs_p()
        clone_args = ["clone", repo.url]
        ref = None
        if repo.tag:
            ref = repo.tag
        elif repo.branch:
            ref = repo.branch
        if ref:
            clone_args.extend(["--branch", ref])
        if self.workspace.shallow:
            clone_args.extend(["--depth", "1"])
        clone_args.append(name)
        try:
            tsrc.git.run_git(parent, *clone_args)
        except tsrc.Error:
            raise tsrc.Error("Cloning failed")

    def reset_repo(self, repo: tsrc.Repo) -> None:
        repo_path = self.workspace.joinpath(repo.src)
        ref = repo.sha1
        if ref:
            ui.info_2("Resetting", repo.src, "to", ref)
            try:
                tsrc.git.run_git(repo_path, "reset", "--hard", ref)
            except tsrc.Error:
                raise tsrc.Error("Resetting to", ref, "failed")

    def process(self, repo: tsrc.Repo) -> None:
        ui.info(repo.src)
        self.check_shallow_with_sha1(repo)
        self.clone_repo(repo)
        self.reset_repo(repo)


Copy = NewType('Copy', Tuple[str, str])


class FileCopier(tsrc.executor.Task[Copy]):
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def description(self) -> str:
        return "Copying files"

    def display_item(self, item: Copy) -> str:
        src, dest = item
        return "%s -> %s" % (src, dest)

    def process(self, item: Copy) -> None:
        src, dest = item
        ui.info(src, "->", dest)
        try:
            src_path = self.workspace.joinpath(src)
            dest_path = self.workspace.joinpath(dest)
            if dest_path.exists():
                # Re-set the write permissions on the file:
                dest_path.chmod(stat.S_IWRITE)
            src_path.copy(dest_path)
            # Make sure perms are read only for everyone
            dest_path.chmod(0o10444)
        except Exception as e:
            raise tsrc.Error(str(e))


class RemoteSetter(tsrc.executor.Task[tsrc.Repo]):
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def quiet(self) -> bool:
        return True

    def description(self) -> str:
        return "Setting remote URLs"

    def display_item(self, repo: tsrc.Repo) -> str:
        return repo.src

    def process(self, repo: tsrc.Repo) -> None:
        try:
            self.try_process_repo(repo)
        except Exception as error:
            raise tsrc.Error(repo.src, ":", "Failed to set remote url to %s" % repo.url, error)

    def try_process_repo(self, repo: tsrc.Repo) -> None:
        full_path = self.workspace.joinpath(repo.src)
        rc, old_url = tsrc.git.run_git_captured(
            full_path,
            "remote", "get-url", "origin",
            check=False,
        )
        if rc == 0:
            self.process_repo_remote_exists(repo, old_url=old_url)
        else:
            self.process_repo_add_remote(repo)

    def process_repo_remote_exists(self, repo: tsrc.Repo, *, old_url: str) -> None:
        full_path = self.workspace.joinpath(repo.src)
        if old_url != repo.url:
            ui.info_2(repo.src, old_url, "->", repo.url)
            tsrc.git.run_git(full_path, "remote", "set-url", "origin", repo.url)

    def process_repo_add_remote(self, repo: tsrc.Repo) -> None:
        full_path = self.workspace.joinpath(repo.src)
        tsrc.git.run_git(full_path, "remote", "add", "origin", repo.url)


class BadBranches(tsrc.Error):
    pass


class Syncer(tsrc.executor.Task[tsrc.Repo]):
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace
        self.bad_branches = list()  # type: List[Tuple[str, str, str]]

    def description(self) -> str:
        return "Synchronize workspace"

    def display_item(self, repo: tsrc.Repo) -> str:
        return repo.src

    def process(self, repo: tsrc.Repo) -> None:
        ui.info(repo.src)
        repo_path = self.workspace.joinpath(repo.src)
        self.fetch(repo_path)
        ref = None

        if repo.tag:
            ref = repo.tag
        elif repo.sha1:
            ref = repo.sha1

        if ref:
            self.sync_repo_to_ref(repo_path, ref)
        else:
            self.check_branch(repo, repo_path)
            self.sync_repo_to_branch(repo_path)

    def check_branch(self, repo: tsrc.Repo, repo_path: Path) -> None:
        current_branch = None
        try:
            current_branch = tsrc.git.get_current_branch(repo_path)
        except tsrc.Error:
            raise tsrc.Error("Not on any branch")

        # FIXME: is repo.branch allowed to be None ?
        if current_branch and current_branch != repo.branch:
            self.bad_branches.append((repo.src, current_branch, repo.branch))  # type: ignore

    @staticmethod
    def fetch(repo_path: Path) -> None:
        try:
            tsrc.git.run_git(repo_path, "fetch", "--tags", "--prune", "origin")
        except tsrc.Error:
            raise tsrc.Error("fetch failed")

    @staticmethod
    def sync_repo_to_ref(repo_path: Path, ref: str) -> None:
        ui.info_2("Resetting to", ref)
        status = tsrc.git.get_status(repo_path)
        if status.dirty:
            raise tsrc.Error("%s dirty, skipping")
        try:
            tsrc.git.run_git(repo_path, "reset", "--hard", ref)
        except tsrc.Error:
            raise tsrc.Error("updating ref failed")

    @staticmethod
    def sync_repo_to_branch(repo_path: Path) -> None:
        try:
            tsrc.git.run_git(repo_path, "merge", "--ff-only", "@{u}")
        except tsrc.Error:
            raise tsrc.Error("updating branch failed")

    def display_bad_branches(self) -> None:
        if not self.bad_branches:
            return
        ui.error("Some projects were not on the correct branch")
        headers = ("project", "actual", "expected")
        data = [
            ((ui.bold, name), (ui.red, actual), (ui.green, expected)) for
            (name, actual, expected) in self.bad_branches
        ]
        ui.info_table(data, headers=headers)
        raise BadBranches()