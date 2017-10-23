import os.path

import ruamel.yaml

import tsrc.manifest
from tsrc.repo import Repo

import pytest


def test_load():
    contents = """
gitlab:
  url: http://gitlab.example.com
repos:
  - src: foo
    url: git@example.com:foo.git
    branch: next

  - src: bar
    url: git@example.com:foo.git
    branch: master
    sha1: ad2b68539c78e749a372414165acdf2a1bb68203

  - src: master
    url: git@example.com:master.git
    tag: v0.1
    copy:
      - src: top.cmake
        dest: CMakeLists.txt
      - src: .clang-format
"""
    manifest = tsrc.manifest.Manifest()
    parsed = ruamel.yaml.safe_load(contents)
    manifest.load(parsed)
    assert manifest.gitlab["url"] == "http://gitlab.example.com"
    assert manifest.get_repos() == [
        tsrc.Repo(
            url="git@example.com:foo.git",
            src="foo",
            branch="next",
            sha1=None,
            tag=None
        ),
        tsrc.Repo(
            url="git@example.com:foo.git",
            src="bar",
            branch="master",
            sha1="ad2b68539c78e749a372414165acdf2a1bb68203",
            tag=None
        ),
        tsrc.Repo(
            url="git@example.com:master.git",
            src="master",
            branch="master",
            sha1=None,
            tag="v0.1",
        ),
    ]
    assert manifest.copyfiles == [
        (os.path.join("master", "top.cmake"), "CMakeLists.txt"),
        (os.path.join("master", ".clang-format"), ".clang-format"),
    ]


def test_find():
    contents = """
repos:
  - src: foo
    url: git@example.com:proj_one/foo

  - src: bar
    url: git@example.com:proj_two/bar
"""
    manifest = tsrc.manifest.Manifest()
    parsed = ruamel.yaml.safe_load(contents)
    manifest.load(parsed)
    assert manifest.get_url("foo") == "git@example.com:proj_one/foo"
    assert manifest.get_url("bar") == "git@example.com:proj_two/bar"
    with pytest.raises(tsrc.manifest.RepoNotFound) as e:
        manifest.get_url("no/such")
        assert "no/such" in e.value.message


def test_validates(tmp_path):
    contents = """
repos:
  - src: bar
    url: baz
    copy:
      - src: foo
        dest: bar
gitlab:
  url: foo
"""
    manifest_path = tmp_path.joinpath("manifest.yml")
    manifest_path.write_text(contents)
    res = tsrc.manifest.load(manifest_path)
    assert res


class ReposGetter:
    def __init__(self, tmp_path):
        self.tmp_path = tmp_path
        self.contents = None

    def get_repos(self, groups=None, all_=None):
        manifest_path = self.tmp_path.joinpath("manifest.yml")
        manifest_path.write_text(self.contents)
        manifest = tsrc.manifest.load(manifest_path)
        return [repo.src for repo in manifest.get_repos(groups=groups, all_=all_)]


@pytest.fixture
def repos_getter(tmp_path):
    return ReposGetter(tmp_path)


def test_default_group(repos_getter):
    contents = """
repos:
  - { src: one, url: one.com }
  - { src: two, url: two.com }
  - { src: three, url: three.com }

groups:
  default:
    repos: [one, two]
"""
    repos_getter.contents = contents
    assert repos_getter.get_repos(groups=None) == ["one", "two"]


def test_specific_group(repos_getter):
    contents = """
repos:
  - { src: any, url: any.com }
  - { src: linux1, url: linux1.com }
  - { src: linux2, url: linux2.com }

groups:
  default:
    repos: [any]
  linux:
    repos: [linux1, linux2]
"""
    repos_getter.contents = contents
    assert repos_getter.get_repos(groups=["default", "linux"]) == ["any", "linux1", "linux2"]


def test_inclusion(repos_getter):
    contents = """
repos:
  - { src: a, url: a.com }
  - { src: b, url: b.com }
  - { src: c, url: c.com }

groups:
  a_group:
    repos: [a]
  b_group:
     repos: [b]
     includes: [a_group]
  c_group:
      repos: [c]
      includes: [b_group]
"""
    repos_getter.contents = contents
    assert repos_getter.get_repos(groups=["c_group"]) == ["a", "b", "c"]


def test_all_repos(repos_getter):
    contents = """
repos:
  - { src: one, url: one.com }
  - { src: two, url: two.com }

groups:
  default:
    repos: [one]
"""
    repos_getter.contents = contents
    assert repos_getter.get_repos(all_=False) == ["one"]
    assert repos_getter.get_repos(all_=True) == ["one", "two"]
