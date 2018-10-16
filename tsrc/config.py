""" Parse tsrc config files """

from path import Path
import ruamel.yaml
import schema
from typing import Any, Dict, NewType
import xdg

import tsrc

Config = NewType('Config', Dict[str, Any])


def parse_config(file_path: Path, config_schema: schema.Schema, roundtrip: bool = False) -> Config:
    try:
        contents = file_path.text()
    except OSError as os_error:
        raise tsrc.InvalidConfig(file_path, os_error)
    try:
        if roundtrip:
            yaml = ruamel.yaml.YAML(typ="rt")
        else:
            yaml = ruamel.yaml.YAML(typ="safe", pure=True)
        parsed = yaml.load(contents)
    except ruamel.yaml.error.YAMLError as yaml_error:
        raise tsrc.InvalidConfig(file_path, yaml_error)
    try:
        config_schema.validate(parsed)
    except schema.SchemaError as schema_error:
        raise tsrc.InvalidConfig(file_path, schema_error)
    return Config(parsed)


def dump_config(config: Config, path: Path) -> None:
    yaml = ruamel.yaml.YAML()
    with path.open("w") as fileobj:
        yaml.dump(config, fileobj)


def get_tsrc_config_path() -> Path:
    config_path = Path(xdg.XDG_CONFIG_HOME)
    config_path = config_path / "tsrc.yml"
    return config_path


def dump_tsrc_config(config: Config) -> None:
    file_path = get_tsrc_config_path()
    dump_config(config, file_path)


def parse_tsrc_config(config_path: Path = None, roundtrip: bool = False) -> Config:
    auth_schema = {
        schema.Optional("gitlab"): {"token": str},
        schema.Optional("github"): {"token": str},
    }
    tsrc_schema = schema.Schema({"auth": auth_schema})
    if not config_path:
        config_path = get_tsrc_config_path()
    return parse_config(config_path, tsrc_schema, roundtrip=roundtrip)
