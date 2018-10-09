from typing import List, Optional
import textwrap
import os.path

import ruamel.yaml

import tsrc
from path import Path

import pytest


def test_load() -> None:
    contents = """
gitlab:
  url: http://gitlab.example.com
repos:
  - src: foo
    url: git@example.com:foo.git
    branch: next

  - src: bar
    url: git@example.com:bar.git
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
    manifest = tsrc.Manifest()
    parsed = ruamel.yaml.safe_load(contents)
    manifest.load(parsed)
    assert manifest.gitlab
    assert manifest.gitlab["url"] == "http://gitlab.example.com"
    assert manifest.get_repos() == [
        tsrc.Repo(
            remotes=[tsrc.repo.Remote(name="origin", url="git@example.com:foo.git")],
            src="foo",
            branch="next",
            sha1=None,
            tag=None
        ),
        tsrc.Repo(
            remotes=[tsrc.repo.Remote(name="origin", url="git@example.com:bar.git")],
            src="bar",
            branch="master",
            sha1="ad2b68539c78e749a372414165acdf2a1bb68203",
            tag=None
        ),
        tsrc.Repo(
            remotes=[tsrc.repo.Remote(name="origin", url="git@example.com:master.git")],
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


def test_get_repo() -> None:
    contents = """
repos:
  - src: foo
    url: git@example.com:proj_one/foo

  - src: bar
    url: git@example.com:proj_two/bar
"""
    manifest = tsrc.Manifest()
    parsed = ruamel.yaml.safe_load(contents)
    manifest.load(parsed)

    def assert_clone_url(src: str, url: str) -> None:
        repo = manifest.get_repo(src)
        assert repo.clone_url == url

    assert_clone_url("foo", "git@example.com:proj_one/foo")
    assert_clone_url("bar", "git@example.com:proj_two/bar")
    with pytest.raises(tsrc.manifest.RepoNotFound) as e:
        manifest.get_repo("no/such")
        assert "no/such" in e.value.message


def test_remotes() -> None:
    contents = """
repos:
  - src: foo
    url: git@example.com/foo
    remotes:
      - name: upstream
        url: git@upstream.com/foo
"""
    manifest = tsrc.manifest.Manifest()
    parsed = ruamel.yaml.safe_load(contents)
    manifest.load(parsed)
    one_repo = manifest.get_repo("foo")
    assert len(one_repo.remotes) == 1


def assert_valid_schema(tmp_path: Path, contents: str) -> tsrc.manifest.Manifest:
    manifest_path = tmp_path / "manifest.yml"
    manifest_path.write_text(textwrap.dedent(contents))
    res = tsrc.manifest.load(manifest_path)
    return res


def assert_invalid_schema(tmp_path: Path, contents: str) -> tsrc.Error:
    manifest_path = tmp_path / "manifest.yml"
    manifest_path.write_text(textwrap.dedent(contents))
    try:
        tsrc.manifest.load(manifest_path)
    except tsrc.InvalidConfig as error:
        return error
    pytest.fail("Did not raise tsrc.InvalidConfig")


def test_validates(tmp_path: Path) -> None:
    assert_valid_schema(
        tmp_path,
        """
        repos:
          - src: bar
            url: baz
            copy:
              - src: foo
                dest: bar
        gitlab:
          url: foo
        """
    )


def test_allow_url(tmp_path: Path) -> None:
    assert_valid_schema(
        tmp_path,
        """
          repos:
            - { src: bar, url: git@example.com/bar }
         """
    )


def test_allow_several_remotes(tmp_path: Path) -> None:
    assert_valid_schema(
        tmp_path,
        """
          repos:
            - { src: bar, url: git@example.com/bar }
          """
    )


def test_disallow_url_and_remotes(tmp_path: Path) -> None:
    error = assert_invalid_schema(
        tmp_path,
        """
        repos:
          - src: bar
            url: git@example.com/bar
            remotes:
            - { name: upstream, url: git@upstream.com/bar }
        """
    )
    assert "remotes" in error.message
    assert "url" in error.message


class ReposGetter:
    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path
        self.contents = ""

    def get_repos(self, groups: Optional[List[str]] = None, all_: bool = False) -> List[str]:
        manifest_path = self.tmp_path / "manifest.yml"
        manifest_path.write_text(self.contents)
        manifest = tsrc.manifest.load(manifest_path)
        return [repo.src for repo in manifest.get_repos(groups=groups, all_=all_)]


@pytest.fixture
def repos_getter(tmp_path: Path) -> ReposGetter:
    return ReposGetter(tmp_path)


def test_default_group(repos_getter: ReposGetter) -> None:
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


def test_specific_group(repos_getter: ReposGetter) -> None:
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


def test_inclusion(repos_getter: ReposGetter) -> None:
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


def test_all_repos(repos_getter: ReposGetter) -> None:
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
