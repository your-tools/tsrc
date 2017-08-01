import sys
from setuptools import setup, find_packages

if sys.version_info.major < 2:
    sys.exit("Error: Please upgrade to Python3")

setup(name="tsrc",
      version="0.1",
      description="Manage multiple repositories",
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
      entry_points={
        "console_scripts": [
          "tsrc = tsrc.cli.main:main",
         ]
      }
      )
