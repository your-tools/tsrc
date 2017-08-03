#!/bin/bash

set -e

mkdocs build
(
  cd ../tsrc-doc
  rm -fr *
  cp -r ../tsrc/site/* .
  git add .
  git commit -m 'Update doc'
  git push
)
