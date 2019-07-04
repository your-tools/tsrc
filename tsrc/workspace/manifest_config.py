from typing import Any, Dict, Optional, List  # noqa
import argparse

import attr
from path import Path
import ruamel.yaml

import tsrc.config

# TODO: should have url xor file_path
MANIFEST_CONFIG_SCHEMA = schema.Schema(
    {
        schema.Optional("url"): str,
        schema.Optional("file_path"): str,
        schema.Optional("branch"): str,
        schema.Optional("tag"): str,
        schema.Optional("groups"): [str],
        schema.Optional("shallow"): bool,
    }
)


@attr.s
class ManifestConfig:
    url = attr.ib(default=None)  # type: str
    branch = attr.ib(default="master")  # type: str
    tag = attr.ib(default=None)  # type: Optional[str]
    shallow = attr.ib(default=False)  # type: bool
    groups = attr.ib(default=list())  # type: List[str]
    file_path = attr.ib(default=None)  # type: Path

    @classmethod
    def from_dict(cls, as_dict: Dict[str, Any]) -> "ManifestConfig":
        res = ManifestConfig()
        res.url = as_dict.get("url")
        res.branch = as_dict.get("branch", "master")
        res.tag = as_dict.get("tag")
        res.shallow = as_dict.get("shallow", False)
        res.groups = as_dict.get("groups") or list()
        file_path = as_dict.get("file_path")
        if file_path:
            res.file_path = Path(file_path)
        return res

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "ManifestConfig":
        as_dict = vars(args)  # type: Dict[str, Any]
        return cls.from_dict(as_dict)

    @classmethod
    def from_file(cls, cfg_path: Path) -> "ManifestConfig":
        as_dict = tsrc.config.parse_config(
            cfg_path, MANIFEST_CONFIG_SCHEMA
        )  # type: Dict[str, Any]
        return cls.from_dict(as_dict)

    def save_to_file(self, cfg_path: Path) -> None:
        cfg_path.parent.makedirs_p()
        as_dict = self.as_dict()
        with cfg_path.open("w") as fp:
            ruamel.yaml.dump(as_dict, fp)

    def as_dict(self) -> Dict[str, Any]:
        res = dict()  # type: Dict[str, Any]
        if self.url:
            res["url"] = self.url
        if self.file_path:
            res["file_path"] = str(self.file_path)
        res["branch"] = self.branch
        if self.tag:
            res["tag"] = self.tag
        if self.groups:
            res["groups"] = self.groups
        res["shallow"] = self.shallow
        return res
