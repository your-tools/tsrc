""" Helpers for github web API """


import getpass
import uuid

import github3
import ui

import tsrc.config


class GitHubAPIError(tsrc.Error):
    def __init__(self, url, status_code, message):
        super().__init__(message)
        self.url = url
        self.status_code = status_code
        self.message = message

    def __str__(self):
        return "%s - %s" % (self.status_code, self.message)


def get_previous_token():
    config = tsrc.config.parse_tsrc_config()
    auth = config.get("auth")
    if not auth:
        return None
    github_auth = auth.get("github")
    if not github_auth:
        return None
    return github_auth.get("token")


def generate_token():
    ui.info_1("Creating new GitHub token")
    username = ui.ask_string("Please enter you GitHub username")
    password = getpass.getpass("Password: ")

    scopes = ['repo']

    # Need a different note for each device, otherwise
    # gh_api.authorize() will fail
    note = "tsrc-" + str(uuid.uuid4())
    note_url = "https://supertanker.github.io/tsrc"

    def ask_2fa():
        return ui.ask_string("2FA code: ")

    authorization = github3.authorize(username, password, scopes,
                                      note=note, note_url=note_url,
                                      two_factor_callback=ask_2fa)
    return authorization.token


def save_token(token):
    cfg_path = tsrc.config.get_tsrc_config_path()
    if cfg_path.exists():
        config = tsrc.config.parse_tsrc_config(roundtrip=True)
    else:
        config = dict()
    if "auth" not in config:
        config["auth"] = dict()
    auth = config["auth"]
    if "github" not in config:
        auth["github"] = dict()
    auth["github"]["token"] = token
    tsrc.config.dump_tsrc_config(config)


def ensure_token():
    token = get_previous_token()
    if not token:
        token = generate_token()
        save_token(token)
    return token


def request_reviewers(repo, pr_number, reviewers):
    owner_name = repo.owner.login
    repo_name = repo.name
    # github3.py does not provide any way to request reviewers, so
    # we have to use private members here
    # pylint: disable=protected-access
    url = repo._build_url(
        "repos", owner_name, repo_name, "pulls", pr_number, "requested_reviewers"
    )
    # pylint: disable=protected-access
    ret = repo._post(url, data={"reviewers": reviewers})
    if not 200 <= ret.status_code < 300:
        raise GitHubAPIError(url, ret.status_code, ret.json().get("message"))


def login():
    token = ensure_token()
    gh_api = github3.GitHub()
    gh_api.login(token=token)
    ui.info_2("Successfully logged in on GitHub")
    return gh_api
