from path import Path
import ui

import tsrc
import tsrc.executor


class RemoteSetter(tsrc.executor.Task[tsrc.Repo]):
    def __init__(self, workspace_path: Path) -> None:
        self.workspace_path = workspace_path

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
        full_path = self.workspace_path.joinpath(repo.src)
        remotes = repo.remotes
        origin_remote = tsrc.repo.Remote("origin", repo.url)
        remotes.insert(0, origin_remote)
        for remote in remotes:
            rc, old_url = tsrc.git.run_git_captured(
                full_path,
                "remote", "get-url", remote.name,
                check=False,
            )
            if rc == 0:
                self.process_repo_remote_exists(repo, remote, old_url=old_url)
            else:
                self.process_repo_add_remote(repo, remote)

    def process_repo_remote_exists(self, repo: tsrc.Repo, remote: tsrc.repo.Remote, *,
                                   old_url: str) -> None:
        full_path = self.workspace_path.joinpath(repo.src)
        if old_url != repo.url:
            ui.info_2(repo.src)
            ui.info(ui.blue, "->", ui.reset, ui.brown, remote.name, ui.reset, repo.url)
            tsrc.git.run_git(full_path, "remote", "set-url", remote.name, remote.url)

    def process_repo_add_remote(self, repo: tsrc.Repo, remote: tsrc.repo.Remote) -> None:
        full_path = self.workspace_path.joinpath(repo.src)
        ui.info_2(repo.src)
        ui.info(ui.blue, "++", ui.reset, ui.brown, remote.name, ui.reset, repo.url)
        tsrc.git.run_git(full_path, "remote", "add", remote.name, remote.url)
