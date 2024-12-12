from dataclasses import dataclass, field, fields
from enum import Enum, Flag, unique
from pathlib import Path
from typing import Any, List, Optional, Union

from tsrc.workspace import Workspace


@unique
class SourceModeEnum(Enum):
    NONE = 0
    RAW_DUMP = 1
    WORKSPACE_DUMP = 2
    YAML_FILE = 3  # not implemented


@unique
class UpdateSourceEnum(Enum):
    NONE = 0
    FILE = 1
    DEEP_MANIFEST = 2


@dataclass
class ManifestDataOptions:
    sha1_only: bool = False
    skip_manifest: bool = False
    only_manifest: bool = False
    ignore_groups: bool = False  # not implemented

    def clean(self) -> None:
        for i in dir(self):
            if isinstance(getattr(self, i), bool) is True:
                setattr(self, i, False)


class FinalOutputModeFlag(Flag):
    NONE = 0
    PREVIEW = 1
    NEW = 2  # use: 'destination_path'
    # if there is no NEW, that means we are using same file for
    # output as we are using for update. thus there cannot be a OVERWRITE
    UPDATE = 4  # use: 'update_path'
    OVERWRITE = 8  # must use force


@dataclass
class FinalOutputAllPaths:
    """
    There may not be clear what output path will be used in the end,
    therefore we should keep them all and take one at the very end
    """

    default_path: Path = Path("manifest.yml")  # use when there is no other
    update_on_path: Optional[Path] = None  # when using update|update_on
    save_to_path: Optional[Path] = None  # whenever there should be a new file
    common_path: Optional[Path] = None  # when on RAW mode, this gets calculated

    def __init__(self, **kwargs: Any) -> None:
        # only set those that are present
        names = {f.name for f in fields(self)}
        for key, value in kwargs.items():
            if key in names:
                setattr(self, key, value)

    def clean_all_paths(self) -> None:
        for i in dir(self):
            if isinstance(getattr(self, i), Path) and i != "default_path":
                setattr(self, i, None)


@dataclass
class DumpManifestOperationDetails:
    """
    Contains all data that should be used
    initially for 'dump-manifest' command

    There are cases however that will require
    to further checks during execution time
    (for example when COMMON PATH will be in place)
    """

    # SOURCE of data (must be set)
    source_mode = SourceModeEnum.NONE
    source_path: Optional[Path] = None

    # UPDATE source (optional)
    update_source = UpdateSourceEnum.NONE
    update_source_path: Optional[Path] = None

    # OPTIONS applied when processing Manifest (optional to change, using defaults)
    manifest_data_options = ManifestDataOptions()

    # FINAL OUTPUT MODE (must be determined)
    final_output_mode: List[FinalOutputModeFlag] = field(default_factory=list)
    final_output_path_list = FinalOutputAllPaths()

    # helpers to be used later
    workspace: Optional[Workspace] = None

    def __init__(self, **kwargs: Any) -> None:
        # fix missing value
        if "final_output_mode" not in fields(self):
            self.final_output_mode: List[FinalOutputModeFlag] = []

        # only set those that are present
        names = {f.name for f in fields(self)}
        for key, value in kwargs.items():
            if key in names:
                setattr(self, key, value)

    def clean(self) -> None:
        self.final_output_path_list.clean_all_paths()
        self.final_output_mode = []
        self.manifest_data_options.clean()

    # ----------
    # 'get_path' - section
    # ----------
    # it is used as for 'final_output_path' only

    def get_path_for_new(self) -> Union[Path, None]:
        if self.final_output_path_list.save_to_path:
            return self.final_output_path_list.save_to_path
        if self.final_output_path_list.common_path:
            return self.final_output_path_list.common_path
        if self.final_output_path_list.default_path:
            return self.final_output_path_list.default_path

        return None

    def get_path_for_update(self) -> Union[Path, None]:
        if self.final_output_path_list.save_to_path:
            return self.final_output_path_list.save_to_path
        if self.final_output_path_list.update_on_path:
            return self.final_output_path_list.update_on_path
        if self.final_output_path_list.common_path:
            return self.final_output_path_list.common_path

        return None
