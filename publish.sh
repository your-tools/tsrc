#!/bin/bash

set -x
set -e

mkdocs gh-deploy

rm -fr dist/
python setup.py sdist bdist_wheel
twine upload dist/*
