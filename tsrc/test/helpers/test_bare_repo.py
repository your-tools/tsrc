from path import Path
import tsrc.git
from .bare_repo import BareRepo


def test_can_clone_created_repo(tmp_path: Path) -> None:
    foo_repo = BareRepo.create(tmp_path / "foo.git")
    url = foo_repo.url

    work_path = tmp_path / "work"
    work_path.mkdir()
    tsrc.git.run(work_path, "clone", url)
    readme = work_path / "foo" / "README"
    assert readme.exists()


def test_create_with_devel_branch(tmp_path: Path) -> None:
    foo_repo = BareRepo.create(tmp_path / "foo.git", branch="devel")
    assert foo_repo.branches() == ["devel"]


def test_ensure_file(tmp_path: Path) -> None:
    foo_repo = BareRepo.create(tmp_path / "foo.git")
    foo_repo.ensure_file("foo.txt")

    work_path = tmp_path / "work"
    work_path.mkdir()
    tsrc.git.run(work_path, "clone", foo_repo.url)
    foo_txt = work_path / "foo" / "foo.txt"
    assert foo_txt.exists()


def test_create_tag(tmp_path: Path) -> None:
    foo_repo = BareRepo.create(tmp_path / "foo.git")
    foo_repo.tag("v1.0")

    _, out = tsrc.git.run_captured(tmp_path, "ls-remote", foo_repo.url)
    assert "v1.0" in out


def test_get_tags(tmp_path: Path) -> None:
    foo_repo = BareRepo.create(tmp_path / "foo.git")
    foo_repo.tag("v1.0")
    assert foo_repo.tags() == ["v1.0"]


def test_get_sha1(tmp_path: Path) -> None:
    foo_repo = BareRepo.create(tmp_path / "foo.git")
    sha1 = foo_repo.get_sha1("master")
    assert isinstance(sha1, str)


def test_ensure_file_on_other_branch(tmp_path: Path) -> None:
    foo_repo = BareRepo.create(tmp_path / "foo.git")
    foo_repo.create_branch("devel")
    foo_repo.ensure_file("devel.txt", branch="devel")

    work_path = tmp_path / "work"
    work_path.mkdir()
    tsrc.git.run(work_path, "clone", foo_repo.url)
    cloned_path = work_path / "foo"
    devel_txt = cloned_path / "devel.txt"
    assert not devel_txt.exists()

    tsrc.git.run(cloned_path, "checkout", "-b", "devel", "origin/devel")
    assert devel_txt.exists()


def test_open_after_create(tmp_path: Path) -> None:
    foo_repo = BareRepo.create(tmp_path / "foo.git")

    foo_repo2 = BareRepo(foo_repo.url)
    foo_repo2.create_branch("devel")

    _, out = tsrc.git.run_captured(tmp_path, "ls-remote", foo_repo.url)
    assert "devel" in out


def test_delete_branch(tmp_path: Path) -> None:
    foo_repo = BareRepo.create(tmp_path / "foo.git")
    foo_repo.create_branch("devel")
    assert set(foo_repo.branches()) == {"master", "devel"}

    foo_repo.delete_branch("devel")
    assert set(foo_repo.branches()) == {"master"}
