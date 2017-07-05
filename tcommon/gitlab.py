""" Tiny wrapper for gitlab REST API """

import netrc
import os
import shutil
import urllib.parse
import zipfile

import path
import requests

import tcommon
from tcommon import ui

GITLAB_URL = "http://10.100.0.1:8000"
GITLAB_API_URL = GITLAB_URL + "/api/v3"


class GitLabError(tcommon.Error):
    def __init__(self, message):
        super().__init__(*message)


def get_token():
    netrc_parser = netrc.netrc()
    unused_login, unused_account, password = netrc_parser.authenticators("gitlab")
    return password


def make_request(verb, url, *, data=None, params=None, stream=False):
    token = get_token()
    full_url = GITLAB_API_URL + url
    response = requests.request(verb, full_url,
                                headers={"PRIVATE-TOKEN": token},
                                data=data, params=params, stream=stream)
    return response


def get_project_id(project_name):
    encoded_project_name = urllib.parse.quote(project_name, safe=list())
    res = make_request("GET", "/projects/%s" % encoded_project_name)
    res.raise_for_status()
    return res.json()["id"]


def extract_latest_artifact(project_name, job_name, dest_path, *, ref="master"):
    """ Get the last successful  artifact from the given project
    and extract it.

    It's always a .zip archive named 'artifact'
    Note: all the files in bin/ will have exec permission
    """
    http_response = make_artifact_download_request(project_name, job_name, ref=ref)
    extract_artifact(http_response, dest_path)


def make_artifact_download_request(project_name, job_name, ref="master"):
    ui.info_1("Looking for latest artifact for", project_name, "on", ref)
    project_id = get_project_id(project_name)
    url = "/projects/%i/jobs/artifacts/%s/download" % (project_id, ref)
    return make_request("GET", url, params={"job": job_name}, stream=True)


def extract_artifact(http_response, dest_path):
    output = dest_path.joinpath("artifact.zip")
    with output.open("wb") as fp:
        shutil.copyfileobj(http_response.raw, fp)
    archive = zipfile.ZipFile(output)
    for member in archive.infolist():
        if member.filename.endswith("/"):
            continue
        member_path = path.Path(member.filename)
        dirname = member_path.dirname()
        basename = member_path.basename()
        dest_path.joinpath(dirname).makedirs_p()
        dest = dest_path.joinpath(dirname, basename)
        data = archive.read(member)
        ui.info_2("x", dest)
        with dest.open("wb") as fp:
            fp.write(data)
        if dirname.name == "bin":
            os.chmod(dest, 0o10755)


def find_opened_merge_request(project_id, source_branch):
    url = "/projects/%s/merge_requests" % project_id
    response = make_request("GET", url)
    response.raise_for_status()
    previous_mrs = response.json()
    for mr in previous_mrs:
        if mr["source_branch"] == source_branch:
            if mr["state"] == "opened":
                return mr


def project_name_form_url(url):
    """
    >>> project_name_form_url(git@example.com:foo/bar.git)
    'foo/bar'
    """
    return "/".join(url.split("/")[-2:]).replace(".git", "")


def create_merge_request(project_id, source_branch, *,
                         target_branch="master", title=None):
    if not title:
        title = source_branch
    ui.info_2("Creating merge request", ui.ellipsis, end="")
    url = "/projects/%i/merge_requests" % project_id
    data = {
        "source_branch": source_branch,
        "target_branch": target_branch,
        "title": title,
        "project_id": project_id,
    }
    result = make_request("POST", url, data=data).json()
    if "error" in result:
        raise GitLabError(result["error"])
    ui.info("done", ui.check)
    return result


def ensure_merge_request(project_id, source_branch, *,
                         title=None, target_branch="master",
                         assignee=None):
    merge_request = find_opened_merge_request(project_id, source_branch)
    if not merge_request:
        merge_request = create_merge_request(project_id, source_branch,
                                             target_branch=target_branch, title=title)
    else:
        ui.info_2("Found existing merge request !%s" % merge_request["iid"])
    remove_source_branch_on_merge(merge_request)
    if assignee:
        assign_merge_request(merge_request, assignee)
    return merge_request


def remove_source_branch_on_merge(merge_request):
    ui.info_2("Set source branch to be removed", ui.ellipsis, end="")
    project_id = merge_request["target_project_id"]
    merge_request_id = merge_request["id"]
    url = "/projects/%s/merge_requests/%s" % (project_id, merge_request_id)
    data = {
        "remove_source_branch": True
    }
    response = make_request("PUT", url, data=data)
    response.raise_for_status()
    ui.info("done", ui.check)


def assign_merge_request(merge_request, assignee):
    ui.info_2("Assigning merge request to", assignee["name"], ui.ellipsis, end="")
    project_id = merge_request["target_project_id"]
    merge_request_id = merge_request["id"]
    url = "/projects/%s/merge_requests/%s" % (project_id, merge_request_id)
    data = {
        "assignee_id": assignee["id"]
    }
    response = make_request("PUT", url, data=data)
    response.raise_for_status()
    ui.info("done", ui.check)


def accept_merge_request(merge_request):
    project_id = merge_request["project_id"]
    merge_request_id = merge_request["id"]
    ui.info_2("Merging when build succeeds", ui.ellipsis, end="")
    url = "/projects/%s/merge_requests/%s/merge" % (project_id, merge_request_id)
    data = {
        "merge_when_build_succeeds": True,
    }
    response = make_request("PUT", url, data=data)
    response.raise_for_status()
    ui.info("done", ui.check)


def get_active_users():
    response = make_request("GET", "/users", params={"active": "true"})
    response.raise_for_status()
    return response.json()
