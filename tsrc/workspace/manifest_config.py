from typing import Any, Dict, List, Optional  # noqa

import attr
from path import Path
import ruamel.yaml

import tsrc.config


@attr.s
class ManifestConfig:
    """ Persistent configuration of the manifest

    For instance, when using `tsrc init --file /path/to/manifest`, we want to
    remember that manifest comes from a file, and then use this
    information later on when running `tsrc sync`
    """

    # Note: ruaml does not know how to serialize Path objects,
    # so we always convert self.file_path to and from strings
    # when reading/saving to files
    url = attr.ib(default=None)  # type: str
    branch = attr.ib(default="master")  # type: str
    tag = attr.ib(default=None)  # type: Optional[str]
    shallow = attr.ib(default=False)  # type: bool
    groups = attr.ib(default=list())  # type: List[str]
    file_path = attr.ib(default=None)  # type: Optional[Path]

    @classmethod
    def from_dict(cls, as_dict: Dict[str, Any]) -> "ManifestConfig":
        res = ManifestConfig(**as_dict)
        not_none = [x for x in (res.url, res.file_path) if x is not None]
        if len(not_none) != 1:
            raise tsrc.Error(
                "Manifest should be configured with either url or file path"
            )
        return res

    @classmethod
    def from_file(cls, cfg_path: Path) -> "ManifestConfig":
        as_dict = tsrc.config.parse_config(cfg_path)  # type: Dict[str, Any]
        file_path = as_dict.get("file_path")
        if file_path:
            as_dict["file_path"] = Path(file_path)
        return cls.from_dict(as_dict)

    def save_to_file(self, cfg_path: Path) -> None:
        cfg_path.parent.makedirs_p()
        as_dict = attr.asdict(self)
        file_path = as_dict.get("file_path")
        if file_path:
            as_dict["file_path"] = str(file_path)
        with cfg_path.open("w") as fp:
            ruamel.yaml.safe_dump(as_dict, fp)
