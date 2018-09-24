from typing import Optional, List  # noqa
import argparse

import attr
from path import Path
import schema

import tsrc.config

OPTIONS_SCHEMA = schema.Schema({
    "url": str,
    schema.Optional("branch"): str,
    schema.Optional("tag"): str,
    schema.Optional("groups"): [str],
    schema.Optional("shallow"): bool,
})


@attr.s
class Options:
    url = attr.ib(default=None)  # type: str
    branch = attr.ib(default="master")  # type: str
    tag = attr.ib(default=None)  # type: Optional[str]
    shallow = attr.ib(default=False)  # type: bool
    groups = attr.ib(default=list())  # type: List[str]


def options_from_dict(as_dict: dict) -> Options:
    res = Options()
    res.url = as_dict["url"]
    res.branch = as_dict.get("branch", "master")
    res.tag = as_dict.get("tag")
    res.shallow = as_dict.get("shallow", False)
    res.groups = as_dict.get("groups") or list()
    return res


def options_from_args(args: argparse.Namespace) -> Options:
    as_dict = vars(args)  # type: dict
    return options_from_dict(as_dict)


def options_from_file(cfg_path: Path) -> Options:
    as_dict = tsrc.config.parse_config_file(cfg_path, OPTIONS_SCHEMA)  # type: dict
    return options_from_dict(as_dict)
