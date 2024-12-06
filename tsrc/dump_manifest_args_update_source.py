import argparse
import os

import cli_ui as ui

from tsrc.dump_manifest_args_data import (
    DumpManifestOperationDetails,
    FinalOutputModeFlag,
    UpdateSourceEnum,
)
from tsrc.dump_manifest_args_source_mode import SourceModeEnum
from tsrc.git import GitStatus, run_git_captured
from tsrc.groups_to_find import GroupsToFind
from tsrc.pcs_repo import get_deep_manifest_from_local_manifest_pcsrepo


class UpdateSource:

    def __init__(
        self, args: argparse.Namespace, dmod: DumpManifestOperationDetails
    ) -> None:
        self.args = args
        self.dmod = dmod

    def get_update_source_and_path(self) -> DumpManifestOperationDetails:

        self._possible_mismatch_on_dump_path()

        self._allow_only_1_update_on_a_time()

        # decide on mode
        if self.args.do_update is True:
            # obtaining data - part
            if self.dmod.source_mode == SourceModeEnum.WORKSPACE_DUMP or (
                self.dmod.source_mode == SourceModeEnum.RAW_DUMP
            ):
                self._get_dm_load_path()
        elif self.args.update_on:
            # test if such file exists
            self._update_on_file_must_exist()

            # we have data ready - no operation after this block in here
            self.dmod.update_source = UpdateSourceEnum.FILE
            self.dmod.update_source_path = self.args.update_on
            self.dmod.final_output_path_list.update_on_path = self.args.update_on
            self.dmod.final_output_mode.append(FinalOutputModeFlag.UPDATE)

        return self.dmod

    def _possible_mismatch_on_dump_path(self) -> None:
        # if we want to update Workspace Manifest with data from RAW dump
        if (
            self.args.raw_dump_path
            and self.args.do_update is True  # noqa: W503
            and self.args.just_preview is False  # noqa: W503
        ):
            dump_path = self.args.raw_dump_path
            if self.args.raw_dump_path.is_absolute() is False:
                dump_path = os.getcwd() / self.args.raw_dump_path
            if self.args.workspace_path:
                if self.args.workspace_path.is_absolute() is False:
                    root_path = os.getcwd() / self.args.workspace_path
                else:
                    root_path = self.args.workspace_path
            else:
                root_path = os.getcwd()

            if os.path.normpath(dump_path) != os.path.normpath(root_path):
                if self.args.use_force is False:
                    raise Exception(
                        "Please consider again what you are trying to do.\nYou want to update Manifest in the Workspace by RAW dump, yet you want to start dump not from Workspace root.\nThis may lead to strange Manifest.\nIf you are still sure that this is what you want, use '--force'."  # noqa: E501
                    )

    def _allow_only_1_update_on_a_time(self) -> None:
        # just 1 update type at a time
        if self.args.do_update is True and self.args.update_on:  # noqa: W503
            raise Exception("Use only one out of '--update' or '--update-on' at a time")

    def _update_on_file_must_exist(self) -> None:
        if self.args.update_on:
            # check if provided file actually exists
            if self.args.update_on.is_file() is False:
                raise Exception("'UPDATE_AT' file does not exists")

    """
    =====================
    obtaining data - part
    =====================
    """

    def _get_dm_load_path(self) -> None:
        # obtains load_path as path of Deep Manifest repository
        dm_is_dirty: bool = False

        gtf = GroupsToFind(self.args.groups)
        dm = None
        if self.dmod.workspace:
            dm, _ = get_deep_manifest_from_local_manifest_pcsrepo(
                self.dmod.workspace,
                gtf,
            )
            if dm:
                self.dmod.update_source_path = (
                    self.dmod.workspace.root_path / dm.dest / "manifest.yml"
                )
                # look for git status if it is not dirty
                gits = GitStatus(self.dmod.workspace.root_path / dm.dest)
                gits.update()
                dm_is_dirty = gits.dirty
                if dm_is_dirty is True:
                    # verify if 'manifest.yml' alone is dirty
                    _, out_stat = run_git_captured(
                        self.dmod.workspace.root_path / dm.dest,
                        "status",
                        "--porcelain=1",
                        "manifest.yml",
                        check=False,
                    )
                    if out_stat == "":
                        # cancel dirty flag if 'manifest.yml' is clean
                        dm_is_dirty = False

        if (
            dm_is_dirty is True
            and self.args.use_force is False  # noqa: W503
            and not self.args.save_to  # noqa: W503
            and self.args.just_preview is False  # noqa: W503
        ):
            raise Exception(
                "not updating Deep Manifest as it is dirty, use '--force' to overide or '--save-to' somewhere else"  # noqa: E501
            )

        if self.dmod.update_source_path:
            ui.info_2("Loading Deep Manifest from", self.dmod.update_source_path)

            # save such path as possible output path
            self.dmod.final_output_path_list.update_on_path = (
                self.dmod.update_source_path
            )
            self.dmod.update_source = UpdateSourceEnum.DEEP_MANIFEST
            self.dmod.final_output_mode.append(FinalOutputModeFlag.UPDATE)

        else:
            raise Exception("Cannot obtain Deep Manifest from Workspace to update")
