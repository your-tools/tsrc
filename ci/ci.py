import multiprocessing
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

    append_check("pycodestyle", "pycodestyle", ".")
    append_check("pyflakes",    sys.executable, "ci/run-pyflakes.py")
    append_check("mccabe",      sys.executable, "ci/run-mccabe.py", "10")
    append_check("pylint",      "pylint", "tsrc", "--score", "no")
    append_check("pytest",      "pytest", "--cov", ".", "--cov-report", "term", "-n", str(nprocs))
    append_check("docs",        "mkdocs", "build")
    return res


def main():
    ui.info_1("Starting CI")
    checks = init_checks()
    for check in checks:
        check.run()
    failed_checks = [check for check in checks if not check.ok]
    if not failed_checks:
        ui.info(ui.green, "CI passed")
    for check in failed_checks:
        ui.error(check.name, "failed")


if __name__ == "__main__":
    main()
