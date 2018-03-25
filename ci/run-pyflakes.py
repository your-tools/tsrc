from path import Path
import subprocess
import sys


def ignore(p):
    parts = p.splitall()
    if any(x.startswith(".") for x in parts):
        return True
    if parts[-1] == "__init__.py":
        return True
    return False


def collect_sources():
    top_path = Path(".")
    for py_path in top_path.walkfiles("*.py"):
        py_path = py_path.normpath()  # get rid of the leading '.'
        if not ignore(py_path):
            yield py_path


def run_pyflakes():
    cmd = ["pyflakes"]
    cmd.extend(collect_sources())
    return subprocess.call(cmd)


if __name__ == "__main__":
    rc = run_pyflakes()
    sys.exit(rc)
