import multiprocessing
import os
import subprocess
import sys

import cli_ui as ui


class Check:
    def __init__(self, name, cmd, env=None):
        self.name = name
        self.cmd = cmd
        self.ok = False
        self.env = env

    def run(self):
        ui.info_2(self.name)
        rc = subprocess.call(self.cmd, env=self.env)
        self.ok = (rc == 0)


def init_checks():
    res = list()

    def append_check(name, *cmd, env=None):
        res.append(Check(name, cmd, env=env))

    append_check("flake8", "flake8", ".")

    env = os.environ.copy()
    env["MYPYPATH"] = "stubs/"
    append_check("mypy", "mypy", "tsrc", "--strict", "--ignore-missing-imports", env=env)

    nprocs = multiprocessing.cpu_count()
    pytest_args = ["pytest", "--cov", ".", "--cov-report", "term", "-n", str(nprocs)]
    if os.environ.get("CI"):
        pytest_args.extend(["-p", "no:sugar"])
    append_check("pytest", *pytest_args)

    append_check("docs", "mkdocs", "build")
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
