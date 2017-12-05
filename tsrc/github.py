""" Helpers for github web API """


import getpass
import uuid

import github3
import ui

import tsrc.config


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

    gh_api = github3.GitHub()
    gh_api.login(username, password, two_factor_callback=lambda: ui.ask_string("2FA code: "))

    user = gh_api.user()
    auth = gh_api.authorize(user, password, scopes, note, note_url)
    return auth.token


def save_token(token):
    cfg_path = tsrc.config.get_tsrc_config_path()
    if cfg_path.exists():
        config = tsrc.config.parse_tsrc_config()
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


def login():
    token = ensure_token()
    gh_api = github3.GitHub()
    gh_api.login(token=token)
    ui.info_2("Successfully logged in on GitHub with login", gh_api.user().login)
    return gh_api
