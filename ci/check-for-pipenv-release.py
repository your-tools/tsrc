import pkg_resources
import sys

import requests


def main():
    buggy_release = pkg_resources.parse_version("8.3.2")
    response = requests.get("https://pypi.python.org/pypi/pipenv/json").json()
    latest_release = sorted(response['releases'].keys())[-1]
    latest_release = pkg_resources.parse_version(latest_release)
    if latest_release > buggy_release:
        print("pipenv has been updated to", latest_release)
        sys.exit(1)
    print("Still waiting for a new pipenv release")


if __name__ == "__main__":
    main()
