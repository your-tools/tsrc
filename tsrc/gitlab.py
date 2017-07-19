""" Tiny wrapper for gitlab REST API """

import json
import netrc
import os
import shutil
import urllib.parse
import zipfile

import path
import requests

import tsrc
from tsrc import ui

GITLAB_URL = "http://10.100.0.1:8000"
GITLAB_API_URL = GITLAB_URL + "/api/v4"


class GitLabError(tsrc.Error):
    pass


def get_token():
    netrc_parser = netrc.netrc()
    unused_login, unused_account, password = netrc_parser.authenticators("gitlab")
    return password


def handle_errors(response, stream=False):
    if stream:
        _handle_stream_errors(response)
    else:
        _handle_json_errors(response)


def _handle_json_errors(response):
    # Make sure we always have a dict containing some
    # kind of error:
    json_details = dict()
    try:
        json_details = response.json()
    except json.JSONDecodeError:
        json_details["error"] = ("Expecting json result, got %s" % response.text)

    if 400 <= response.status_code < 500:
        for key in ["error", "message"]:
            if key in json_details:
                raise GitLabError("Client error:", json_details[key])
        raise GitLabError(json_details)
    if response.status_code >= 500:
        raise GitLabError("Server error:", response.text)


def _handle_stream_errors(response):
    if response.status_code >= 400:
        raise GitLabError("Incorrect status code:", response.status_code)


def make_request(verb, url, *, data=None, params=None, stream=False):
    token = get_token()
    full_url = GITLAB_API_URL + url
    response = requests.request(verb, full_url,
                                headers={"PRIVATE-TOKEN": token},
                                data=data, params=params, stream=stream)
    handle_errors(response, stream=stream)
    if stream:
        return response
    else:
        return response.json()


def get_project_id(project_name):
    encoded_project_name = urllib.parse.quote(project_name, safe=list())
    res = make_request("GET", "/projects/%s" % encoded_project_name)
    return res["id"]




def find_opened_merge_request(project_id, source_branch):
    url = "/projects/%s/merge_requests" % project_id
    previous_mrs = make_request("GET", url)
    for mr in previous_mrs:
        if mr["source_branch"] == source_branch:
            if mr["state"] == "opened":
                return mr


def create_merge_request(project_id, source_branch, *, title,
                         target_branch="master"):
    ui.info_2("Creating merge request", ui.ellipsis, end="")
    url = "/projects/%i/merge_requests" % project_id
    data = {
        "source_branch": source_branch,
        "target_branch": target_branch,
        "title": title,
        "project_id": project_id,
    }
    result = make_request("POST", url, data=data)
    ui.info("done", ui.check)
    return result


def update_merge_request(merge_request, **kwargs):
    project_id = merge_request["target_project_id"]
    merge_request_iid = merge_request["iid"]
    url = "/projects/%s/merge_requests/%s" % (project_id, merge_request_iid)
    return make_request("PUT", url, data=kwargs)


def accept_merge_request(merge_request):
    project_id = merge_request["project_id"]
    merge_request_iid = merge_request["iid"]
    ui.info_2("Merging when build succeeds", ui.ellipsis, end="")
    url = "/projects/%s/merge_requests/%s/merge" % (project_id, merge_request_iid)
    data = {
        "merge_when_pipeline_succeeds": True,
    }
    make_request("PUT", url, data=data)
    ui.info("done", ui.check)


def get_active_users():
    return make_request("GET", "/users", params={"active": "true"})
