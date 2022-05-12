from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

import ruamel.yaml


@dataclass
class WorkspaceConfig:
    """Persistent configuration of the workspace.

    Stored in <workspace>/.tsrc/config.yml, and can be
    edited by hand to use a different set of groups
    for instance.
    """

    manifest_url: str
    manifest_branch: str
    repo_groups: List[str]

    shallow_clones: bool = False
    clone_all_repos: bool = False

    singular_remote: Optional[str] = None

    @classmethod
    def from_file(cls, cfg_path: Path) -> "WorkspaceConfig":
        yaml = ruamel.yaml.YAML(typ="rt")
        parsed = yaml.load(cfg_path.read_text())
        return cls(**parsed)

    def save_to_file(self, cfg_path: Path) -> None:
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        yaml = ruamel.yaml.YAML(typ="rt")
        yaml.register_class(Path)
        as_dict = asdict(self)
        with cfg_path.open("w") as fp:
            yaml.dump(as_dict, fp)
