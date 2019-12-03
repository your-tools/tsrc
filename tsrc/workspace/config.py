from typing import List, Optional
import attr
from path import Path
import ruamel.yaml


@attr.s
class WorkspaceConfig:
    """ Persistent configuration of the workspace

    """

    # Note: always use a default value so the ctor only
    # takes named arguments
    manifest_url = attr.ib(default=None)  # type: str
    manifest_branch = attr.ib(default=None)  # type: str

    shallow_clones = attr.ib(default=False)  # type: bool
    repo_groups = attr.ib(default=[])  # type: List[str]
    clone_all_repos = attr.ib(default=False)  # type: bool

    @manifest_url.validator
    def check(self, attribute: str, value: Optional[str] = None) -> None:
        if value is None:
            raise ValueError("manifest_url must not be None")

    @classmethod
    def from_file(cls, cfg_path: Path) -> "WorkspaceConfig":
        yaml = ruamel.yaml.YAML(typ="rt")
        parsed = yaml.load(cfg_path.text())
        return cls(**parsed)

    def save_to_file(self, cfg_path: Path) -> None:
        cfg_path.parent.makedirs_p()
        yaml = ruamel.yaml.YAML(typ="rt")
        yaml.register_class(Path)
        as_dict = attr.asdict(self)
        with cfg_path.open("w") as fp:
            yaml.dump(as_dict, fp)
