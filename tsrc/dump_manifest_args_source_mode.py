import argparse
import os
from pathlib import Path
from typing import Tuple

from tsrc.cli import get_workspace_with_repos
from tsrc.dump_manifest_args_data import DumpManifestOperationDetails, SourceModeEnum


class SourceMode:

    def __init__(
        self, args: argparse.Namespace, dmod: DumpManifestOperationDetails
    ) -> None:
        self.args = args
        self.dmod = dmod

    def get_source_mode_and_path(
        self,
    ) -> Tuple[DumpManifestOperationDetails, argparse.Namespace]:

        self._respect_workspace_path()

        self._decide_source_mode()

        self._get_workspace_if_needed()

        return self.dmod, self.args

    def _respect_workspace_path(self) -> None:
        # when Workspace path is provided by '-w', we have to consider
        # it as root path when relative path is provided for RAW dump
        if (
            self.args.raw_dump_path
            and self.args.workspace_path  # noqa: W503
            and not os.path.isabs(self.args.raw_dump_path)  # noqa: W503
        ):
            self.args.raw_dump_path = Path(
                os.path.join(self.args.workspace_path, self.args.raw_dump_path)
            )

    def _decide_source_mode(self) -> None:
        if self.args.raw_dump_path:
            self.dmod.source_mode = SourceModeEnum.RAW_DUMP
            self.dmod.source_path = self.args.raw_dump_path
        else:
            # right now there are no more 'Source MODEs' implemented
            # therefore any other then RAW MODE is Workspace MODE
            self.dmod.source_mode = SourceModeEnum.WORKSPACE_DUMP

    def _get_workspace_if_needed(self) -> None:
        # determine if Workspace is required
        if not self.args.raw_dump_path or (
            self.args.raw_dump_path and self.args.do_update is True
        ):
            # it will throw Error if there is no Workspace
            self.dmod.workspace = get_workspace_with_repos(self.args)
