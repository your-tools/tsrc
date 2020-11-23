from pathlib import Path
from typing import List, Optional

import attr
import ruamel.yaml


@attr.s
class WorkspaceConfig:
    """Persistent configuration of the workspace.

    Stored in <workspace>/.tsrc/config.yml, and can be
    edited by hand to use a different set of groups
    for instance.
    """

    manifest_url = attr.ib()  # type: str
    manifest_branch = attr.ib()  # type: str
    repo_groups = attr.ib()  # type: List[str]

    shallow_clones = attr.ib(default=False)  # type: bool
    clone_all_repos = attr.ib(default=False)  # type: bool

    singular_remote = attr.ib(default=None)  # type: Optional[str]

    @manifest_url.validator
    def check(self, attribute: str, value: Optional[str] = None) -> None:
        if value is None:
            raise ValueError("manifest_url must not be None")

    @classmethod
    def from_file(cls, cfg_path: Path) -> "WorkspaceConfig":
        yaml = ruamel.yaml.YAML(typ="rt")
        parsed = yaml.load(cfg_path.read_text())
        return cls(**parsed)

    def save_to_file(self, cfg_path: Path) -> None:
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        yaml = ruamel.yaml.YAML(typ="rt")
        yaml.register_class(Path)
        as_dict = attr.asdict(self)
        with cfg_path.open("w") as fp:
            yaml.dump(as_dict, fp)
