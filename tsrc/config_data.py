"""
Config Data

Is designed to help identify (ConfigUpdateType)
config chage/update type
and to keep new data for update (ConfigUpdateData)

All this is so when config is going to be
updated, it can be done in one fell swoop
"""

from dataclasses import dataclass
from enum import Enum, unique
from typing import List, Optional


@unique
class ConfigUpdateType(Enum):
    NONE = 0
    MANIFEST_BRANCH = 1
    REPO_GROUPS = 2
    # add other update types when needed


@dataclass(frozen=True)
class ConfigUpdateData:
    manifest_branch: Optional[str] = None
    repo_groups: Optional[List[str]] = None  # not yet supported
    # add more configuration data when supported
