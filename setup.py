import sys
from setuptools import setup, find_packages

if sys.version_info.major < 3:
    sys.exit("Error: Please upgrade to Python3")


def get_long_description():
    with open("README.rst") as fp:
        return fp.read()


setup(
    name="tsrc",
    version="0.6.2",
    description="Manage multiple repositories",
    long_description=get_long_description(),
    url="https://github.com/SuperTanker/tsrc",
    author="Kontrol SAS",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "attrs",
        "colored_traceback",
        "colorama",
        "github3.py >= 1.0",
        "path.py",
        "python-cli-ui",
        "python-gitlab",
        "pyparsing",
        "requests",
        "ruamel.yaml",
        "schema",
        "tabulate",
        "unidecode",
        "xdg",
    ],
    classifiers=[
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ],
    entry_points={"console_scripts": ["tsrc = tsrc.cli.main:main"]},
)
