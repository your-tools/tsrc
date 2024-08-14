from collections import OrderedDict
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, List, Optional

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
    manifest_branch_0: str
    repo_groups: List[str]

    shallow_clones: bool = False
    clone_all_repos: bool = False

    singular_remote: Optional[str] = None

    def __init__(self, **kwargs: Any) -> None:
        # only set those that are present
        names = {f.name for f in fields(self)}
        for key, value in kwargs.items():
            if key in names:
                setattr(self, key, value)

    @classmethod
    def from_file(cls, cfg_path: Path) -> "WorkspaceConfig":
        yaml = ruamel.yaml.YAML(typ="rt")
        parsed = yaml.load(cfg_path.read_text())
        if not parsed.get("manifest_branch_0"):
            """compatibility fix for older version.
            usefull when transitioning with Workspace initialized
            by older version"""
            parsed["manifest_branch_0"] = parsed.get("manifest_branch")
            parsed = OrderedDict(sorted(parsed.items()))
        return cls(**parsed)

    def save_to_file(self, cfg_path: Path) -> None:
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        yaml = ruamel.yaml.YAML(typ="rt")
        yaml.register_class(Path)
        as_dict = asdict(self)
        with cfg_path.open("w") as fp:
            yaml.dump(as_dict, fp)
