""" Helpers for github web API """

import getpass
import uuid
from typing import cast, List, Optional, Dict, Any

import github3
from github3.repos.repo import Repository
import cli_ui as ui

import tsrc


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
        return dict()
    return cast(Dict[str, Any], auth.get(auth_system, dict()))


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
        config = tsrc.Config(dict())
    if "auth" not in config:
        config["auth"] = dict()
    auth = config["auth"]
    if auth_system not in auth:
        auth[auth_system] = dict()
    auth[auth_system]["token"] = token
    tsrc.config.dump_tsrc_config(config)


def ensure_token(github_client: github3.GitHub, auth_system: str) -> str:
    token = get_previous_token(auth_system=auth_system)
    if not token:
        token = generate_token(github_client=github_client)
        save_token(token=token, auth_system=auth_system)
    return token


def request_reviewers(repo: Repository, pr_number: int, reviewers: List[str]) -> None:
    owner_name = repo.owner.login
    repo_name = repo.name
    # github3.py does not provide any way to request reviewers, so
    # we have to use private members here
    url = repo._build_url(
        "repos", owner_name, repo_name, "pulls", pr_number, "requested_reviewers"
    )
    ret = repo._post(url, data={"reviewers": reviewers})
    if not 200 <= ret.status_code < 300:
        raise GitHubAPIError(url, ret.status_code, ret.json().get("message"))


def login(github_enterprise_url: Optional[str] = None) -> github3.GitHub:
    if github_enterprise_url:
        verify = get_verify_tls_setting(auth_system="github_enterprise")
        gh_api = github3.GitHubEnterprise(url=github_enterprise_url, verify=verify)
        token = ensure_token(github_client=gh_api, auth_system="github_enterprise")
    else:
        gh_api = github3.GitHub()
        token = ensure_token(github_client=gh_api, auth_system="github")

    gh_api.login(token=token)
    ui.info_2("Successfully logged in on GitHub")
    return gh_api
