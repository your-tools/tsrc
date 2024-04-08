from pathlib import Path
from typing import List

import ruamel.yaml

"""helper function(s) follows:
these functions do not take part on testing by itself alone"""


def ad_hoc_deep_manifest_manifest_branch(
    workspace_path: Path,
    branch: str,
) -> None:
    manifest_path = workspace_path / "manifest" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())
    for _, value in parsed.items():
        if isinstance(value, List):
            for x in value:
                if isinstance(x, ruamel.yaml.comments.CommentedMap):
                    if x["dest"] == "manifest":
                        x.insert(2, "branch", branch)

    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)


def ad_hoc_deep_manifest_manifest_url(
    workspace_path: Path,
    url: str,
) -> None:
    manifest_path = workspace_path / "manifest" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    yaml = ruamel.yaml.YAML(typ="rt")
    parsed = yaml.load(manifest_path.read_text())
    for _, value in parsed.items():
        if isinstance(value, List):
            for x in value:
                if isinstance(x, ruamel.yaml.comments.CommentedMap):
                    if x["dest"] == "manifest":
                        x["url"] = url

    with open(manifest_path, "w") as file:
        yaml.dump(parsed, file)
