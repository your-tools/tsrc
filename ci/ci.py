import multiprocessing
import os
import subprocess
import sys

import ui


class Check:
    def __init__(self, name, cmd):
        self.name = name
        self.cmd = cmd
        self.ok = False

    def run(self):
        ui.info_2(self.name)
        rc = subprocess.call(self.cmd)
        self.ok = (rc == 0)


def init_checks():
    res = list()

    def append_check(name, *cmd):
        res.append(Check(name, cmd))

    nprocs = multiprocessing.cpu_count()

    pytest_args = ["pytest", "--cov", ".", "--cov-report", "term", "-n", str(nprocs)]
    if os.environ.get("CI"):
        pytest_args.extend(["-p", "no:sugar"])

    append_check("pycodestyle", "pycodestyle", ".")
    append_check("pyflakes",    sys.executable, "ci/run-pyflakes.py")
    append_check("mccabe",      sys.executable, "ci/run-mccabe.py", "10")
    append_check("mypy",        "mypy", "tsrc", "--ignore-missing-imports")
    append_check("pylint",      "pylint", "tsrc", "--score", "no")
    append_check("pytest",      *pytest_args)
    append_check("docs",        "mkdocs", "build")
    return res


def main():
    ui.info_1("Starting CI")
    all_checks = init_checks()
    check_list = sys.argv[1:]
    checks = all_checks
    if check_list:
        checks = [c for c in checks if c.name in check_list]
    for check in checks:
        check.run()
    failed_checks = [check for check in checks if not check.ok]
    if not failed_checks:
        ui.info(ui.green, "CI passed")
        return
    for check in failed_checks:
        ui.error(check.name, "failed")
    sys.exit(1)


if __name__ == "__main__":
    main()
