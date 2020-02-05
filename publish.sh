#!/bin/bash

set -x
set -e

rm -fr dist/
poetry build
poetry publish
