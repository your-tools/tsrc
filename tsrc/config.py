""" Parse tsrc config files """

from path import Path
import ruamel.yaml
import schema
from typing import Any, Dict, NewType
import xdg

import tsrc

Config = NewType('Config', Dict[str, Any])


def parse_config_file(
        file_path: Path, config_schema: schema.Schema, roundtrip: bool = False) -> Config:
    try:
        contents = file_path.text()
    except OSError as os_error:
        raise tsrc.InvalidConfig(file_path, os_error)
    try:
        if roundtrip:
            parsed = ruamel.yaml.safe_load(contents, ruamel.yaml.RoundTripLoader)
        else:
            parsed = ruamel.yaml.safe_load(contents)
    except ruamel.yaml.error.YAMLError as yaml_error:
        raise tsrc.InvalidConfig(file_path, yaml_error)
    try:
        config_schema.validate(parsed)
    except schema.SchemaError as schema_error:
        raise tsrc.InvalidConfig(file_path, schema_error)
    return Config(parsed)


def get_tsrc_config_path() -> Path:
    config_path = Path(xdg.XDG_CONFIG_HOME)
    config_path = config_path / "tsrc.yml"
    return config_path


def dump_tsrc_config(config: Config) -> None:
    dumped = ruamel.yaml.dump(config, Dumper=ruamel.yaml.RoundTripDumper)
    file_path = get_tsrc_config_path()
    file_path.write_text(dumped)


def parse_tsrc_config(config_path: Path = None, roundtrip: bool = False) -> Config:
    auth_schema = {
        schema.Optional("gitlab"): {"token": str},
        schema.Optional("github"): {"token": str},
    }
    tsrc_schema = schema.Schema({"auth": auth_schema})
    if not config_path:
        config_path = get_tsrc_config_path()
    return parse_config_file(config_path, tsrc_schema, roundtrip=roundtrip)
