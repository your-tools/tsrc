from typing import Dict

from tsrc.git import GitStatus
from tsrc.repo import Repo
from tsrc.workspace import Workspace


class EnvSetter:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace

    def get_env_for_repo(self, repo: Repo) -> Dict[str, str]:
        workspace_vars = get_workspace_vars(self.workspace)

        repo_vars = get_repo_vars(repo)

        repo_path = self.workspace.root_path / repo.dest
        status = GitStatus(repo_path)
        status.update()
        status_vars = get_status_vars(status)

        res = {}
        res.update(repo_vars)
        res.update(status_vars)
        res.update(workspace_vars)
        return res


def get_workspace_vars(workspace: Workspace) -> Dict[str, str]:
    res = {}
    res["TSRC_WORKSPACE_PATH"] = str(workspace.root_path.resolve())
    res["TSRC_MANIFEST_URL"] = workspace.config.manifest_url
    res["TSRC_MANIFEST_BRANCH"] = workspace.config.manifest_branch
    return res


def get_repo_vars(repo: Repo) -> Dict[str, str]:
    res = {}
    res["TSRC_PROJECT_DEST"] = repo.dest
    res["TSRC_PROJECT_MANIFEST_BRANCH"] = repo.branch
    res["TSRC_PROJECT_CLONE_URL"] = repo.clone_url
    if repo.sha1:
        res["TSRC_PROJECT_SHA1"] = repo.sha1
    if repo.tag:
        res["TSRC_PROJECT_TAG"] = repo.tag
    if repo.shallow:
        res["TSRC_PROJECT_SHALLOW"] = "true"
    for remote in repo.remotes:
        key = "TSRC_PROJECT_REMOTE_" + remote.name.upper()
        value = remote.url
        res[key] = value
    return res


def get_status_vars(status: GitStatus) -> Dict[str, str]:
    res = {}
    res["TSRC_PROJECT_STATUS_UNTRACKED"] = str(status.untracked)
    res["TSRC_PROJECT_STATUS_ADDED"] = str(status.added)
    res["TSRC_PROJECT_STATUS_STAGED"] = str(status.staged)
    res["TSRC_PROJECT_STATUS_NOT_STAGED"] = str(status.not_staged)
    res["TSRC_PROJECT_STATUS_BEHIND"] = str(status.behind)
    res["TSRC_PROJECT_STATUS_AHEAD"] = str(status.ahead)
    if status.branch:
        res["TSRC_PROJECT_STATUS_BRANCH"] = status.branch
    if status.sha1:
        res["TSRC_PROJECT_STATUS_SHA1"] = status.sha1
    if status.tag:
        res["TSRC_PROJECT_STATUS_TAG"] = status.tag
    if status.dirty:
        res["TSRC_PROJECT_STATUS_DIRTY"] = "true"
    return res
