set -x
set -e

poetry run black --check tsrc
poetry run flake8 .
poetry run mypy
poetry run mkdocs build
