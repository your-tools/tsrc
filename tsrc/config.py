""" Parse tsrc config files """

from pathlib import Path
from typing import Any, Dict, NewType

import ruamel.yaml
from schema import Schema, SchemaError

from tsrc.errors import InvalidConfig

Config = NewType("Config", Dict[str, Any])


def parse_config(file_path: Path, *, schema: Schema) -> Config:
    """Parse a config given a file path and a schema."""

    # Note: we try and wrap any raised exception into a generic
    # InvalidConfig error, so that error messages always contains
    # the path of the file that caused the error.
    try:
        contents = file_path.read_text()
    except OSError as os_error:
        raise InvalidConfig(file_path, os_error)
    try:
        yaml = ruamel.yaml.YAML(typ="safe", pure=True)
        parsed = yaml.load(contents)
    except ruamel.yaml.error.YAMLError as yaml_error:
        raise InvalidConfig(file_path, yaml_error)
    try:
        schema.validate(parsed)
    except SchemaError as schema_error:
        raise InvalidConfig(file_path, schema_error)
    return Config(parsed)
