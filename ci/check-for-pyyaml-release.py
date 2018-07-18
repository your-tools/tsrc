import pkg_resources
import sys

import requests


def main():
    response = requests.get("https://pypi.python.org/pypi/pyyaml/json").json()
    releases = response["releases"].keys()
    print("releases: ", *releases)
    versions = (pkg_resources.parse_version(x) for x in releases)
    stable_versions = sorted(x for x in versions if not x.is_prerelease)
    next_stable = pkg_resources.parse_version("4.0")
    vulnerable_stable = pkg_resources.parse_version("3.13")
    for version in stable_versions:
        if version > vulnerable_stable or version > next_stable:
            sys.exit("Please upgrade to pyyaml", version)
    print("Still waiting for a non-vulnerable stable pyyaml release")


if __name__ == "__main__":
    main()
