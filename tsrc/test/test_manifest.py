import os.path

import tsrc.manifest
from tsrc.manifest import joinurl

import pytest


def test_load():
    contents = """
gitlab:
  http_url: http://gitlab.example.com

clone_prefix: git@example.com

repos:
  - src: foo
    name: proj/foo

  - src: master
    name: proj/master
    copy:
      - src: top.cmake
        dest: CMakeLists.txt
"""
    manifest = tsrc.manifest.Manifest()
    manifest.load(contents)
    assert manifest.gitlab["http_url"] == "http://gitlab.example.com"
    assert manifest.repos == [
        ("foo", "git@example.com:proj/foo.git"),
        ("master", "git@example.com:proj/master.git")
    ]
    assert manifest.copyfiles == [
        (os.path.join("master", "top.cmake"), "CMakeLists.txt")
    ]


def test_find():
    contents = """
gitlab:
  http_url: http://gitlab.example.com

clone_prefix: ssh://git@example.com:8022

repos:
  - src: foo
    name: proj_one/foo

  - src: bar
    name: proj_two/bar
"""
    manifest = tsrc.manifest.Manifest()
    manifest.load(contents)
    assert manifest.get_url("foo") == "ssh://git@example.com:8022/proj_one/foo.git"
    assert manifest.get_url("bar") == "ssh://git@example.com:8022/proj_two/bar.git"
    with pytest.raises(tsrc.manifest.RepoNotFound) as e:
        manifest.get_url("no/such")
        assert "no/such" in e.value.message


def test_joinurl(git_server):
    bar_url = git_server.add_repo("foo/bar")

    test_data = [
        (("git@example.com", "bar/baz"), "git@example.com:bar/baz.git"),
        (("ssh://git@example.com:8022", "bar/baz"), "ssh://git@example.com:8022/bar/baz.git"),
        ((git_server.clone_prefix, "foo/bar"), bar_url),
    ]
    for input_, output in test_data:
        assert joinurl(*input_) == output
