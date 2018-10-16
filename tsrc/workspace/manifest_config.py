from typing import Any, Dict, Optional, List  # noqa
import argparse

import attr
from path import Path
import schema
import ruamel.yaml

import tsrc.config

MANIFEST_CONFIG_SCHEMA = schema.Schema({
    "url": str,
    schema.Optional("branch"): str,
    schema.Optional("tag"): str,
    schema.Optional("groups"): [str],
    schema.Optional("shallow"): bool,
})


@attr.s
class ManifestConfig:
    url = attr.ib(default=None)  # type: str
    branch = attr.ib(default="master")  # type: str
    tag = attr.ib(default=None)  # type: Optional[str]
    shallow = attr.ib(default=False)  # type: bool
    groups = attr.ib(default=list())  # type: List[str]

    @classmethod
    def from_dict(cls: "ManifestConfig", as_dict: dict) -> "ManifestConfig":
        res = ManifestConfig()
        res.url = as_dict["url"]
        res.branch = as_dict.get("branch", "master")
        res.tag = as_dict.get("tag")
        res.shallow = as_dict.get("shallow", False)
        res.groups = as_dict.get("groups") or list()
        return res

    @classmethod
    def from_args(cls: "ManifestConfig", args: argparse.Namespace) -> "ManifestConfig":
        as_dict = vars(args)  # type: dict
        return cls.from_dict(as_dict)

    @classmethod
    def from_file(cls: "ManifestConfig", cfg_path: Path) -> "ManifestConfig":
        as_dict = tsrc.config.parse_config(cfg_path, MANIFEST_CONFIG_SCHEMA)  # type: dict
        return cls.from_dict(as_dict)

    def save_to_file(self, cfg_path: Path) -> None:
        as_dict = self.as_dict()
        with cfg_path.open("w") as fp:
            ruamel.yaml.dump(as_dict, fp)

    def as_dict(self) -> Dict[str, Any]:
        res = dict()  # type: Dict[str, Any]
        res["url"] = self.url
        res["branch"] = self.branch
        if self.tag:
            res["tag"] = self.tag
        if self.groups:
            res["groups"] = self.groups
        res["shallow"] = self.shallow
        return res
