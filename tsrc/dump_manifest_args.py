import argparse
import os
from copy import deepcopy
from pathlib import Path
from typing import List

import cli_ui as ui

from tsrc.dump_manifest import ManifestDumpersOptions
from tsrc.dump_manifest_args_data import (
    DumpManifestOperationDetails,
    FinalOutputModeFlag,
    ManifestDataOptions,
)
from tsrc.dump_manifest_args_final_output import FinalOutput
from tsrc.dump_manifest_args_source_mode import SourceMode, SourceModeEnum
from tsrc.dump_manifest_args_update_source import UpdateSource
from tsrc.groups_and_constraints_data import (
    GroupsAndConstraints,
    get_group_and_constraints_data,
)


class DumpManifestArgs:
    """
    atempt to separate logic around 'args' and its handling outside of
    DumpManifestsCMDLogic
    """

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args

        # from args, get Group and constraints data
        self.gac: GroupsAndConstraints = get_group_and_constraints_data(args)

        # some (local) helpers
        self.mdo: ManifestDumpersOptions
        self.any_update = args.do_update or bool(args.update_on)
        if self.any_update is True:
            self.mdo = ManifestDumpersOptions(delete_repo=not args.no_repo_delete)
        else:
            self.mdo = ManifestDumpersOptions()

        # this will be returned when no Exception is hit
        self.dmod = DumpManifestOperationDetails()

        # ready source MODE
        self.s_m = SourceMode(args, self.dmod)
        self.dmod, self.args = self.s_m.get_source_mode_and_path()

        # take care of UPDATE source
        self.u_s = UpdateSource(args, self.dmod)
        self.dmod = self.u_s.get_update_source_and_path()

        # take care of OPTIONS of Manifest's handling
        self.dmod.manifest_data_options = self._get_manifest_data_options()

        # take care of Final Output Mode Flag and All Paths
        self.f_o = FinalOutput(args, self.dmod)
        self.dmod = self.f_o.get_final_output_modes_and_paths()

        # take care of default situation: get mode and path
        self.dmod = self._check_default_mode_and_path()

        # take care of Warning of common purpose
        self._take_care_of_common_warnings()

    def _get_manifest_data_options(self) -> ManifestDataOptions:
        mdo = ManifestDataOptions()
        if self.args.sha1_only is True:
            mdo.sha1_only = True
        if self.args.skip_manifest is True:
            mdo.skip_manifest = True
        if self.args.only_manifest is True:
            mdo.only_manifest = True
        if self.args.skip_manifest is True and self.args.only_manifest is True:
            raise Exception(
                "'--skip-manifest' and '--only-manifest' are mutually exclusive"
            )
        return mdo

    def _check_default_mode_and_path(self) -> DumpManifestOperationDetails:
        # use default only if COMMON PATH will not be calculated
        if (
            not self.dmod.final_output_mode
            and self.dmod.source_mode != SourceModeEnum.RAW_DUMP  # noqa: W503
        ):
            if self.dmod.final_output_path_list.default_path.is_file() is True:
                if self.args.use_force is False:
                    raise Exception(
                        f"such file '{self.dmod.final_output_path_list.default_path}' already exists, use '--force' to overwrite it"  # noqa: E501
                    )
                else:

                    # when there is '--force' allow overwrite of default file
                    self.dmod.final_output_mode.append(FinalOutputModeFlag.OVERWRITE)

            else:

                # by default, new file will be created
                self.dmod.final_output_mode.append(FinalOutputModeFlag.NEW)

        return self.dmod

    def _take_care_of_common_warnings(self) -> None:
        if self.args.save_to and self.args.just_preview is True:
            ui.warning("'SAVE_TO' path will be ignored when using '--preview'")

        if self.args.save_to and self.args.update_on:
            ui.warning("'SAVE_TO' path will be ignored when using '--update-on'")

        if self.any_update is True and self.args.just_preview is True:
            ui.warning("When in preview mode, no actual update will be made")

    def consider_common_path(
        self, common_path: List[str]
    ) -> DumpManifestOperationDetails:

        # verify if it is ok to continue
        tmp_save_file = deepcopy(common_path)
        tmp_default_file = str(self.dmod.final_output_path_list.default_path).split(
            os.sep
        )
        tmp_save_file += tmp_default_file
        tmp_save_file_path = Path(os.sep.join(tmp_save_file))
        if self.args.raw_dump_path and not self.args.save_to:  # noqa: W503
            grab_save_path = tmp_save_file_path
            if grab_save_path.is_file():
                if FinalOutputModeFlag.PREVIEW in self.dmod.final_output_mode:
                    return self.dmod
                if self.args.use_force is True:
                    self.dmod.final_output_mode.append(FinalOutputModeFlag.OVERWRITE)
                else:
                    raise Exception(
                        f"Such file '{grab_save_path}' already exists, use '--force' if you want to overwrite it"  # noqa: E501
                    )
            else:
                # create new file only if we are not updating
                if FinalOutputModeFlag.UPDATE not in self.dmod.final_output_mode:
                    self.dmod.final_output_mode.append(FinalOutputModeFlag.NEW)

            # save data
            self.dmod.final_output_path_list.common_path = grab_save_path

        return self.dmod
