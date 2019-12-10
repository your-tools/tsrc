from typing import cast, Any, Optional, Dict, List
import getpass
import uuid

import cli_ui as ui
import github3

import tsrc
from .interface import PullRequest, Repository, Client


class GitHubPullRequest(PullRequest):
    # We need gh_repository to access 'issues' that are really
    # pull requests
    def __init__(self, gh_repository: Any, gh_pull_request: Any):
        self.gh_repository = gh_repository
        self.gh_pull_request = gh_pull_request

    def get_number(self) -> int:
        return self.gh_pull_request.number  # type: ignore

    def get_html_url(self) -> str:
        return self.gh_pull_request.html_url  # type: ignore

    def update(self, *, base: Optional[str], title: Optional[str]) -> None:
        params = {}  # type: Dict[str, str]
        if base is not None:
            params["base"] = base
        if title is not None:
            params["title"] = title
        self.gh_pull_request.update(**params)

    def assign(self, assignee: str) -> None:
        issue = self.gh_repository.issue(self.get_number())
        issue.assign(assignee)

    def request_reviewers(self, reviewers: List[str]) -> None:
        # github3.py does not provide any way to request reviewers, so
        # we have to use private members here
        owner_name = self.gh_repository.owner.login
        repo_name = self.gh_repository.name
        url = self.gh_repository._build_url(
            "repos",
            owner_name,
            repo_name,
            "pulls",
            self.get_number(),
            "requested_reviewers",
        )
        ret = self.gh_repository._post(url, data={"reviewers": reviewers})
        if not 200 <= ret.status_code < 300:
            raise GitHubAPIError(url, ret.status_code, ret.json().get("message"))

    def merge(self) -> None:
        self.gh_pull_request.merge()

    def close(self) -> None:
        self.gh_pull_request.close()


class GitHubRepository(Repository):
    def __init__(self, gh_repository: Any):
        self.gh_repository = gh_repository

    def find_pull_requests(self, *, state: str, head: str) -> List[GitHubPullRequest]:
        gh_pull_requests = self.gh_repository.pull_requests()
        return [
            GitHubPullRequest(self, x)
            for x in gh_pull_requests
            if x.state == state and x.head.ref == head
        ]

    def get_default_branch(self) -> str:
        return self.gh_repository.default_branch  # type: ignore

    def create_pull_request(
        self, *, head: str, base: str, title: str
    ) -> GitHubPullRequest:
        gh_pull_request = self.gh_repository.create_pull(title, base, head)
        return GitHubPullRequest(self, gh_pull_request)


class GitHubApiClient(Client):
    def __init__(self, *, enterprise_url: Optional[str] = None) -> None:
        self.gh_api = login(enterprise_url=enterprise_url)

    def get_repository(self, owner: str, name: str) -> GitHubRepository:
        gl_repository = self.gh_api.repository(owner, name)
        return GitHubRepository(gl_repository)


class GitHubAPIError(tsrc.Error):
    def __init__(self, url: str, status_code: int, message: str) -> None:
        super().__init__(message)
        self.url = url
        self.status_code = status_code
        self.message = message

    def __str__(self) -> str:
        return "%s - %s" % (self.status_code, self.message)


def get_config_auth_object(auth_system: str) -> Dict[str, Any]:
    config = tsrc.config.parse_tsrc_config()
    auth = config.get("auth")
    if not auth:
        return {}
    return cast(Dict[str, Any], auth.get(auth_system, {}))


def get_previous_token(auth_system: str) -> Optional[str]:
    github_auth = get_config_auth_object(auth_system)
    if not github_auth:
        return None
    return cast(Optional[str], github_auth.get("token"))


def get_verify_tls_setting(auth_system: str) -> object:
    github_auth = get_config_auth_object(auth_system)
    if not github_auth:
        return True
    return github_auth.get("verify", True)


def generate_token(github_client: github3.GitHub) -> str:
    ui.info_1("Creating new GitHub token")
    username = ui.ask_string("Please enter you GitHub username")
    password = getpass.getpass("Password: ")

    scopes = ["repo"]

    # Need a different note for each device, otherwise
    # gh_api.authorize() will fail
    note = "tsrc-" + str(uuid.uuid4())
    note_url = "https://TankerHQ.github.io/tsrc"

    def ask_2fa() -> str:
        return cast(str, ui.ask_string("2FA code: "))

    authorization = github3.authorize(
        username,
        password,
        scopes,
        note=note,
        note_url=note_url,
        two_factor_callback=ask_2fa,
        github=github_client,
    )
    return cast(str, authorization.token)


def save_token(token: str, auth_system: str) -> None:
    cfg_path = tsrc.config.get_tsrc_config_path()
    if cfg_path.exists():
        config = tsrc.config.parse_tsrc_config(roundtrip=True)
    else:
        config = tsrc.Config({})
    if "auth" not in config:
        config["auth"] = {}
    auth = config["auth"]
    if auth_system not in auth:
        auth[auth_system] = {}
    auth[auth_system]["token"] = token
    tsrc.config.dump_tsrc_config(config)


def ensure_token(github_client: github3.GitHub, auth_system: str) -> str:
    token = get_previous_token(auth_system=auth_system)
    if not token:
        token = generate_token(github_client=github_client)
        save_token(token=token, auth_system=auth_system)
    return token


def login(enterprise_url: Optional[str] = None) -> github3.GitHub:
    if enterprise_url:
        verify = get_verify_tls_setting(auth_system="github_enterprise")
        gh_api = github3.GitHubEnterprise(url=enterprise_url, verify=verify)
        token = ensure_token(github_client=gh_api, auth_system="github_enterprise")
    else:
        gh_api = github3.GitHub()
        token = ensure_token(github_client=gh_api, auth_system="github")

    gh_api.login(token=token)
    ui.info_2("Successfully logged in on GitHub")
    return gh_api
