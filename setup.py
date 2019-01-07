import sys
from setuptools import setup, find_packages

if sys.version_info.major < 3:
    sys.exit("Error: Please upgrade to Python3")


def get_long_description():
    with open("README.rst") as fp:
        return fp.read()


setup(
    name="tsrc",
    version="0.6.4",
    description="Manage multiple repositories",
    long_description=get_long_description(),
    url="https://github.com/TankerHQ/tsrc",
    author="Kontrol SAS",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "attrs",
        "colored_traceback",
        "colorama",
        "github3.py >= 1.0",
        "path.py",
        "cli-ui>=0.9.1",
        "python-gitlab",
        "pyparsing",
        "requests",
        "ruamel.yaml",
        "schema",
        "tabulate",
        "unidecode",
        "xdg",
    ],
    extras_require={
        "dev": [
            "coverage==4.5.1",
            "pluggy==0.7.1",
            "pytest==3.8.1",
            "pytest-cov==2.6.0",
            "pytest-sugar==0.9.1",
            "pytest-xdist==1.23.2",
            "requests",
            "mock",
            "mypy==0.630",
            "twine",
            "wheel",
            "flake8==3.5.0",
            "flake8-comprehensions",
            "mkdocs",
        ]

    },
    classifiers=[
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ],
    entry_points={"console_scripts": ["tsrc = tsrc.cli.main:main"]},
)
