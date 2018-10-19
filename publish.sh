#!/bin/bash

set -x
set -e

mkdocs gh-deploy

rm -fr dist/
pipenv run python setup.py sdist bdist_wheel
pipenv run twine upload dist/*
