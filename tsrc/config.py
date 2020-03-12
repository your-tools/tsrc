""" Parse tsrc config files """

from path import Path
import ruamel.yaml
import schema
from typing import Any, Dict, NewType, Optional

import tsrc

Config = NewType("Config", Dict[str, Any])


def parse_config(
    file_path: Path, config_schema: Optional[schema.Schema] = None
) -> Config:
    try:
        contents = file_path.text()
    except OSError as os_error:
        raise tsrc.InvalidConfig(file_path, os_error)
    try:
        yaml = ruamel.yaml.YAML(typ="safe", pure=True)
        parsed = yaml.load(contents)
    except ruamel.yaml.error.YAMLError as yaml_error:
        raise tsrc.InvalidConfig(file_path, yaml_error)
    if config_schema:
        try:
            config_schema.validate(parsed)
        except schema.SchemaError as schema_error:
            raise tsrc.InvalidConfig(file_path, schema_error)
    return Config(parsed)
