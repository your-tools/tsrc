""" Tools to manage tsrc workspaces

Mostly used by tsrc/cli.py

"""

import stat
import textwrap

import attr
import ruamel.yaml
import schema
import ui

import tsrc
import tsrc.executor
import tsrc.git
import tsrc.manifest

OPTIONS_SCHEMA = schema.Schema({
    "url": str,
    schema.Optional("branch"): str,
    schema.Optional("tag"): str,
    schema.Optional("groups"): [str],
    schema.Optional("shallow"): bool,
})


# pylint: disable=too-few-public-methods
@attr.s
class Options:
    url = attr.ib(default=None)
    branch = attr.ib(default="master")
    tag = attr.ib(default=None)
    shallow = attr.ib(default=False)
    groups = attr.ib(default=list())


def options_from_dict(as_dict):
    res = Options()
    res.url = as_dict["url"]
    res.branch = as_dict.get("branch", "master")
    res.tag = as_dict.get("tag")
    res.shallow = as_dict.get("shallow", False)
    res.groups = as_dict.get("groups") or list()
    return res


def options_from_args(args):
    as_dict = vars(args)
    return options_from_dict(as_dict)


def options_from_file(cfg_path):
    as_dict = tsrc.config.parse_config_file(cfg_path, OPTIONS_SCHEMA)
    return options_from_dict(as_dict)


class LocalManifest:
    """ Represent a manifest that has been cloned locally inside the
    hidden <workspace>/.tsrc directory, along with its configuration

    """
    def __init__(self, workspace_path):
        hidden_path = workspace_path.joinpath(".tsrc")
        self.clone_path = hidden_path.joinpath("manifest")
        self.cfg_path = hidden_path.joinpath("manifest.yml")
        self.manifest = None

    @property
    def branch(self):
        return self.load_config().branch

    @property
    def shallow(self):
        return self.load_config().shallow

    @property
    def copyfiles(self):
        return self.manifest.copyfiles

    @property
    def active_groups(self):
        return self.load_config().groups

    def get_repos(self):
        return self.manifest.get_repos(groups=self.active_groups)

    def load(self):
        yml_path = self.clone_path.joinpath("manifest.yml")
        if not yml_path.exists():
            message = "No manifest found in {}. Did you run `tsrc init` ?"
            raise tsrc.Error(message.format(yml_path))
        self.manifest = tsrc.manifest.load(yml_path)

    def get_gitlab_url(self):
        assert self.manifest, "manifest is empty. Did you call load()?"
        gitlab_config = self.manifest.gitlab
        if not gitlab_config:
            raise tsrc.Error("No gitlab configuration found in manifest")
        return gitlab_config["url"]

    def get_url(self, src):
        return self.manifest.get_url(src)

    def configure(self, options):
        if not options.url:
            raise tsrc.Error("Manifest URL is required")
        self._ensure_git_state(options)
        self.save_config(options)

    def update(self):
        ui.info_2("Updating manifest")
        if not self.clone_path.exists():
            message = "Could not find manifest in {}. "
            message += "Did you run `tsrc init` ?"
            raise tsrc.Error(message.format(self.clone_path))
        cmd = ("fetch", "--prune", "origin")
        tsrc.git.run_git(self.clone_path, *cmd)
        cmd = ("reset", "--hard", "@{u}")
        tsrc.git.run_git(self.clone_path, *cmd)

    def save_config(self, options):
        config = dict()
        config["url"] = options.url
        config["branch"] = options.branch
        if options.tag:
            config["tag"] = options.tag
        if options.groups:
            config["groups"] = options.groups
        config["shallow"] = options.shallow
        with self.cfg_path.open("w") as fp:
            ruamel.yaml.dump(config, fp)

    def load_config(self):
        return options_from_file(self.cfg_path)

    def _ensure_git_state(self, options):
        if self.clone_path.exists():
            self._reset_manifest_clone(options)
        else:
            self._clone_manifest(options)

    def _reset_manifest_clone(self, options):
        tsrc.git.run_git(self.clone_path, "remote", "set-url", "origin", options.url)

        tsrc.git.run_git(self.clone_path, "fetch")
        tsrc.git.run_git(self.clone_path, "checkout", "-B", options.branch)
        tsrc.git.run_git(self.clone_path, "branch", options.branch,
                         "--set-upstream-to", "origin/%s" % options.branch)
        if options.tag:
            ref = options.tag
        else:
            ref = "origin/%s" % options.branch
        tsrc.git.run_git(self.clone_path, "reset", "--hard", ref)

    def _clone_manifest(self, options):
        parent, name = self.clone_path.splitpath()
        parent.makedirs_p()
        ref = None
        if options.tag:
            ref = options.tag
        elif options.branch:
            ref = options.branch
        args = ("clone", options.url, name)
        if ref:
            args += ("--branch", ref)
        tsrc.git.run_git(self.clone_path.parent, *args)


class Workspace():
    def __init__(self, root_path):
        self.root_path = root_path
        self.local_manifest = LocalManifest(root_path)

    def joinpath(self, *parts):
        return self.root_path.joinpath(*parts)

    def get_repos(self):
        return self.local_manifest.get_repos()

    def load_manifest(self):
        self.local_manifest.load()

    def get_gitlab_url(self):
        return self.local_manifest.get_gitlab_url()

    def configure_manifest(self, manifest_options):
        self.local_manifest.configure(manifest_options)

    def update_manifest(self):
        self.local_manifest.update()

    @property
    def active_groups(self):
        return self.local_manifest.active_groups

    @property
    def shallow(self):
        return self.local_manifest.shallow

    def clone_missing(self):
        """ Clone missing repos.

        Called at the beginning of `tsrc init` and `tsrc sync`

        """
        to_clone = list()
        for repo in self.get_repos():
            repo_path = self.joinpath(repo.src)
            if not repo_path.exists():
                to_clone.append(repo)
        cloner = Cloner(self)
        tsrc.executor.run_sequence(to_clone, cloner)

    def set_remotes(self):
        remote_setter = RemoteSetter(self)
        tsrc.executor.run_sequence(self.get_repos(), remote_setter)

    def copy_files(self):
        file_copier = FileCopier(self)
        tsrc.executor.run_sequence(self.local_manifest.copyfiles, file_copier)

    def sync(self):
        syncer = Syncer(self)
        try:
            tsrc.executor.run_sequence(self.get_repos(), syncer)
        finally:
            syncer.display_bad_branches()

    def enumerate_repos(self):
        """ Yield (index, repo, full_path) for all the repos """
        for i, repo in enumerate(self.get_repos()):
            full_path = self.joinpath(repo.src)
            yield (i, repo, full_path)

    def get_url(self, src):
        """ Return the url of the project in `src` """
        return self.local_manifest.get_url(src)


class Cloner(tsrc.executor.Task):
    def __init__(self, workspace):
        self.workspace = workspace

    def description(self):
        return "Cloning missing repos"

    def display_item(self, repo):
        return repo.src

    def check_shallow_with_sha1(self, repo):
        if not repo.sha1:
            return
        if self.workspace.shallow:
            message = textwrap.dedent(
                "Cannot use --shallow with a fixed sha1 ({repo.sha1})\n"
                "Consider using a tag instead"
            )
            message = message.format(repo=repo)
            ui.fatal(message)

    def clone_repo(self, repo):
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

    def reset_repo(self, repo):
        repo_path = self.workspace.joinpath(repo.src)
        ref = repo.sha1
        if ref:
            ui.info_2("Resetting", repo.src, "to", ref)
            try:
                tsrc.git.run_git(repo_path, "reset", "--hard", ref)
            except tsrc.Error:
                raise tsrc.Error("Resetting to", ref, "failed")

    def process(self, repo):
        ui.info(repo.src)
        self.check_shallow_with_sha1(repo)
        self.clone_repo(repo)
        self.reset_repo(repo)


class FileCopier(tsrc.executor.Task):
    def __init__(self, workspace):
        self.workspace = workspace

    def description(self):
        return "Copying files"

    def display_item(self, item):
        src, dest = item
        return "%s -> %s" % (src, dest)

    def process(self, item):
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


class RemoteSetter(tsrc.executor.Task):
    def __init__(self, workspace):
        self.workspace = workspace

    def quiet(self):
        return True

    def description(self):
        return "Setting remote URLs"

    def display_item(self, repo):
        return repo.src

    def process(self, repo):
        full_path = self.workspace.joinpath(repo.src)
        try:
            _, old_url = tsrc.git.run_git(full_path, "remote", "get-url", "origin", raises=False)
            if old_url != repo.url:
                ui.info_2(repo.src, old_url, "->", repo.url)
                tsrc.git.run_git(full_path, "remote", "set-url", "origin", repo.url)
        except Exception:
            raise tsrc.Error(repo.src, ":", "Failed to set remote url to %s" % repo.url)


class BadBranches(tsrc.Error):
    pass


class Syncer(tsrc.executor.Task):
    def __init__(self, workspace):
        self.workspace = workspace
        self.bad_branches = list()

    def description(self):
        return "Synchronize workspace"

    def display_item(self, repo):
        return repo.src

    def process(self, repo):
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

    def check_branch(self, repo, repo_path):
        current_branch = None
        try:
            current_branch = tsrc.git.get_current_branch(repo_path)
        except tsrc.Error:
            raise tsrc.Error("Not on any branch")

        if current_branch and current_branch != repo.branch:
            self.bad_branches.append((repo.src, current_branch, repo.branch))

    @staticmethod
    def fetch(repo_path):
        try:
            tsrc.git.run_git(repo_path, "fetch", "--tags", "--prune", "origin")
        except tsrc.Error:
            raise tsrc.Error("fetch failed")

    @staticmethod
    def sync_repo_to_ref(repo_path, ref):
        ui.info_2("Resetting to", ref)
        status = tsrc.git.get_status(repo_path)
        if status.dirty:
            raise tsrc.Error("%s dirty, skipping")
        try:
            tsrc.git.run_git(repo_path, "reset", "--hard", ref)
        except tsrc.Error:
            raise tsrc.Error("updating ref failed")

    @staticmethod
    def sync_repo_to_branch(repo_path):
        try:
            tsrc.git.run_git(repo_path, "merge", "--ff-only", "@{u}")
        except tsrc.Error:
            raise tsrc.Error("updating branch failed")

    def display_bad_branches(self):
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
