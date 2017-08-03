import sys
from setuptools import setup, find_packages

if sys.version_info.major < 3:
    sys.exit("Error: Please upgrade to Python3")


def get_long_description():
    with open("README.rst") as fp:
        return fp.read()


setup(name="tsrc",
      version="0.1.3",
      description="Manage multiple repositories",
      long_description=get_long_description(),
      url="https://github.com/TankerApp/tsrc",
      author="Kontrol SAS",
      packages=find_packages(),
      include_package_data=True,
      install_requires=[
        "colored_traceback",
        "colorama",
        "path.py",
        "pyparsing",
        "requests",
        "ruamel.yaml",
        "unidecode",
        "xdg",
      ],
      classifiers=[
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
      ],
      entry_points={
        "console_scripts": [
          "tsrc = tsrc.cli.main:main",
         ]
      }
      )
