# FinalOutput (ModeFlag|AllPaths)
import argparse
import os

from tsrc.dump_manifest_args_data import (
    DumpManifestOperationDetails,
    FinalOutputModeFlag,
)


class FinalOutput:

    def __init__(
        self, args: argparse.Namespace, dmod: DumpManifestOperationDetails
    ) -> None:
        self.args = args
        self.dmod = dmod

    def get_final_output_modes_and_paths(self) -> DumpManifestOperationDetails:

        # on '--preview'
        self._take_care_of__preview()

        # on '--save_to'
        self._take_care_of__save_to()

        return self.dmod

    def _take_care_of__preview(self) -> None:
        if self.args.just_preview is True:
            # no output path in this case
            self.dmod.final_output_mode.append(FinalOutputModeFlag.PREVIEW)

    def _take_care_of__save_to(self) -> None:
        if self.args.save_to:
            if self.args.save_to.is_dir() is True:
                self.args.save_to = self.args.save_to / "manifest.yml"
            elif (
                os.path.dirname(self.args.save_to)
                and os.path.isdir(os.path.dirname(self.args.save_to))  # noqa: W503
                is False  # noqa: W503
            ):
                raise Exception(
                    f"'SAVE_TO' directory structure must exists, however '{os.path.dirname(self.args.save_to)}' does not"  # noqa: E501
                )
            if self.args.save_to.is_file() is True:
                if (
                    self.args.use_force is False
                    and FinalOutputModeFlag.PREVIEW  # noqa: W503
                    not in self.dmod.final_output_mode
                ):
                    raise Exception(
                        f"'SAVE_TO' file exist, use '--force' to overwrite existing file, or use '--update-on {self.args.save_to}' instead"  # noqa: E501
                    )
                else:

                    # set data only in regard of output
                    self.dmod.final_output_mode.append(FinalOutputModeFlag.OVERWRITE)
                    self.dmod.final_output_path_list.save_to_path = self.args.save_to

            else:

                # set data only in regard of output
                self.dmod.final_output_mode.append(FinalOutputModeFlag.NEW)
                self.dmod.final_output_path_list.save_to_path = self.args.save_to
