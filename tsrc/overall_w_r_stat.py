"""Overall Workspace Repositories Status:

IN CONSTRUCTION/WORK IN PROGRESS

It will not be just Manifest.
For 'status' command we can output how many
repositories is in inconsistant state"""

from dataclasses import dataclass
from enum import Enum, unique
from typing import Union

# from tsrc.manifest import Manifest
from tsrc.pcs_repo import PCSRepo


@unique
class StatusFooterUseCaseMode(Enum):
    MANIFEST = 1
    STATUS = 2


@dataclass(frozen=True)
class OverallWRStat:
    manifest_branch: str
    manifest_branch_0: str
    mode: StatusFooterUseCaseMode = StatusFooterUseCaseMode.MANIFEST
    pcs_repo: Union[PCSRepo, None] = None
    is_manifest_repo_ready: Union[bool, None] = None
    manifest_branch_change: Union[bool, None] = None
    manifest_branch_change_from: Union[str, None] = None

    # Deep Manifest related:
    d_m_same_remote_url: Union[bool, None] = None

    # not implemented in status_footer.py
    # TODO: rewrite to 'None' as default to all
    is_manifest_repo_branch_need_create: bool = False
    is_manifest_repo_need_push: bool = False
    is_manifest_same_remote_url: bool = True
    is_manifest_same_remote_sha: bool = True
    # TODO: add List of inconsistant repository for 'status'
    # TODO: if any some other feature is found, add it here
