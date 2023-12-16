# type: ignore
from invoke import call, task

SOURCES = "tsrc"


@task
def black(c, check=False):
    print("Running black")
    cmd = f"black {SOURCES}"
    if check:
        cmd += " --check"
    c.run(cmd)


@task
def isort(c, check=False):
    print("Running isort")
    cmd = f"isort {SOURCES}"
    if check:
        cmd += " --check"
    c.run(cmd)


@task
def flake8(c):
    print("Running flake8")
    c.run(f"flake8 {SOURCES}")


@task
def mypy(c, machine_readable=False):
    print("Running mypy")
    cmd = "mypy"
    if machine_readable:
        cmd += " --no-pretty"
    else:
        cmd += " --color-output --pretty"
    c.run(cmd)


@task
def test(c):
    print("Running pytest")
    c.run("pytest -n auto", pty=True)


@task(
    pre=[
        call(black, check=True),
        call(isort, check=True),
        call(flake8),
        call(mypy),
    ]
)
def lint(c):
    pass
