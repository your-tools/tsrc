set -x
set -e

poetry run flake8 .
poetry run mypy
poetry run mkdocs build
