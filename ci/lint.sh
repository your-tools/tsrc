#!/bin/bash -xe

export PYTHONPATH=.
pycodestyle .
python3 ci/run-pyflakes.py
python3 ci/run-mccabe.py 10
pylint tsrc --score=no
