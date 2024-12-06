""" Entry point for `tsrc dump-manifest`.

This is actually one of the few commands that does not need to have Workspace.
In fact, we can start the project with this command by using RAW dump
to create current Manifest file, which we can put to new GIT Repository,
push it to remote and then calls 'tsrc init'.

RAW dump (mode of operation):
    RAW dump means we are creating/updating Manifest WITHOUT Workspace.
    So we do not have '.tscr/config' or any other '.tsrc' data
    (not even Groups if they are not present in Manifest when we updating it)

Simplest way to start a new 'tsrc' project by creating Manifest is to prepare
every repository into some dedicated directory and from there call:

'tsrc dump-manifest --raw .'

Which creates Manifest file there. Which you can place into some other
directory, push to some remote and call:

'tsrc init <url_of_remote_of_manifest>'

Which will create 'tsrc' Workspace right there.
"""

import argparse
import io
from pathlib import Path
from typing import Dict, List, Tuple, Union, cast

import cli_ui as ui
from ruamel.yaml import YAML

from tsrc.cli import (
    add_num_jobs_arg,
    add_repos_selection_args,
    add_workspace_arg,
    get_num_jobs,
)
from tsrc.dump_manifest import ManifestDumper
from tsrc.dump_manifest_args import DumpManifestArgs
from tsrc.dump_manifest_args_data import (
    FinalOutputModeFlag,
    SourceModeEnum,
    UpdateSourceEnum,
)
from tsrc.dump_manifest_helper import MRISHelpers
from tsrc.dump_manifest_raw_grabber import ManifestRawGrabber
from tsrc.errors import MissingRepoError
from tsrc.executor import process_items
from tsrc.file_system import make_relative
from tsrc.repo import Repo
from tsrc.status_endpoint import CollectedStatuses, Status, StatusCollector
from tsrc.utils import erase_last_line


def configure_parser(subparser: argparse._SubParsersAction) -> None:
    parser = subparser.add_parser(
        "dump-manifest",
        description="Dump Manifest by obtaining data from one of these 2 MODES: from RAW SOURCE or from Workspace. Optionaly use obtained data to UPDATE exising YAML file (can also update Deep Manifest). And at the end, write output to DESTINATION considering PROPERTIES. By default Workspace MODE is used as data source and 'manifest.yml' in Workspace root path is used as DESTINATION. No UPDATE is done by default. 'manifest.yml' filename is default everytime directory is provided, but the file is required.",  # noqa: E501
    )
    parser.add_argument(
        "-r",
        "--raw",
        type=Path,
        help="WARNING: for this, execution Path DOES matter. It switch MODE to RAW dump, settig SOURCE to provided Path (relative to WORKSPACE_PATH if set, or to execution Path otherwise) to search for any GIT repositories recursively to be used as data source. by default DESTINATION is 'manifest.yml' in COMMON PATH. COMMON PATH is calculated during execution time on given directory structure of where Repos are located as the deepest common root of all Repos while keeping each Repo directory its own",  # noqa: E501
        dest="raw_dump_path",
    )
    parser.add_argument(
        "-u",
        "--update",
        action="store_true",
        help="Regardles of operation mode, it will always look for Deep Manifest and set it as UPDATE source and DESTINATION default",  # noqa: E501
        dest="do_update",
    )
    parser.add_argument(
        "-U",
        "--update-on",
        help="Set UPDATE operation mode, by setting the UPDATE source and DESTINATION default to provided UPDATE_AT path to YAML file. Such path must exists",  # noqa: E501
        type=Path,
        dest="update_on",
    )
    parser.add_argument(
        "--no-repo-delete",
        action="store_true",
        help="Disallow to delete any Repo record from existing Manifest. This have only meaning when on UPDATE operation mode",  # noqa: E501
        dest="no_repo_delete",
    )
    parser.add_argument(
        "--sha1-only",
        action="store_true",
        help="Use SHA1 as only value (with branch if available) for every considered Repo. This is particulary useful when we want to point to exact point of Repos states",  # noqa: E501
        dest="sha1_only",
    )
    parser.add_argument(
        "-X",
        "--skip-manifest",
        help="Skip manifest repository if found. If not, it is ignored. For this filter to work, the Workspace needs to be present. And it is only applied after the processing of the Repositories",  # noqa: E501
        dest="skip_manifest",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "-M",
        "--only-manifest",
        help="Only work with manifest repository if found. If not, the Error is thrown that list of Repositories ends up empty. For this filter to work, the Workspace needs to be present. And it is only applied after the processing of the Repositories",  # noqa: E501
        dest="only_manifest",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "-p",
        "--preview",
        action="store_true",
        help="Set DESTINATION to stdout ignoring any previous DESTINATION defaults. This option has the higher priority out of all modifying DESTINATION. No filesystem write operation will be made",  # noqa: E501
        dest="just_preview",
    )
    parser.add_argument(
        "-s",
        "--save-to",
        help="Set DESTINATION to Path or Filename, ignoring any previous DESTINATION defaults. if Path is directory, it will be extended by default Manifest's filename",  # noqa: E501
        type=Path,
        dest="save_to",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Set PROPERTY to allow dangerous operations, like overwrite an already existing file. Use with care",  # noqa: E501
        dest="use_force",
    )
    add_workspace_arg(parser)
    add_repos_selection_args(parser)
    add_num_jobs_arg(parser)
    parser.set_defaults(run=run)


def run(args: argparse.Namespace) -> None:

    try:
        # checking args and preparing its data
        a = DumpManifestArgs(args)

        # if no Exception was hit, we can continue
        # to actual processing the command
        ddm = DumpManifestsCMDLogic(a, num_jobs=get_num_jobs(args))

        ddm.get_data()

        if ddm.yy:
            ddm.output_data()
    except Exception as e:
        ui.error(e)
    finally:
        if "a" in locals():
            a.dmod.clean()


class DumpManifestsCMDLogic:
    """
    Check and prepare arguments, perform operations on filesystem (if needed),
    everything but not actual YAML data handling and/or processing.
    For that the 'DumpManifest' and 'ManifestRawGrabber' classes are dedicated.
    """

    def __init__(self, a: DumpManifestArgs, num_jobs: int) -> None:
        # default presets for output YAML
        self.yaml = YAML()  # for final output
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        self.yaml.allow_duplicate_keys = True
        self.yaml.default_flow_style = False  # this makes a huge difference

        # output data
        self.yy: Union[Dict, List, None] = None
        self.is_updated: Union[bool, None] = None

        # everything in regard of args
        self.a = a

        # translate MRISHelpers's data into YAML-useful data
        # it can also update on existing data
        self.m_du = ManifestDumper()
        self.num_jobs = num_jobs

    """
    ===== 'get_data' section =====
    """

    def get_data(self) -> None:

        # prepare 'mris_h' dataclass
        try:
            if self.a.dmod.source_mode == SourceModeEnum.RAW_DUMP:
                repos = self._get_data_get_repos()
                if not repos:
                    raise Exception("cannot obtain data: no Repos were found")
                self.mris_h = MRISHelpers(repos=repos)
            elif self.a.dmod.source_mode == SourceModeEnum.WORKSPACE_DUMP:
                statuses, w_repos = self._get_data_get_statuses()
                for _, status in statuses.items():
                    if not (
                        isinstance(status, MissingRepoError)
                        or isinstance(status, Exception)  # noqa: W503
                    ):
                        break
                else:
                    raise Exception("cannot obtain data: no useful Repos were found")
                self.mris_h = MRISHelpers(statuses=statuses, w_repos=w_repos)
            else:
                raise Exception("cannot detect dump operation mode")
        except Exception as e:
            raise (e)

        # only up to this Fn the 'statuses' and 'repos' are relevant
        # we will work with 'mris_h' right after this comment

        self._get_yaml_data()

    def _get_data_get_repos(self) -> List[Repo]:

        # grab Repos
        try:
            if self.a.dmod.source_path:
                mgr = ManifestRawGrabber(self.a, self.a.dmod.source_path)
                repos, self.a = mgr.grab(self.num_jobs)
                if (
                    self.a.args.skip_manifest is True
                    or self.a.args.only_manifest is True  # noqa: W503
                ):
                    if self.a.dmod.workspace:
                        repos, _ = self.m_du.filter_repos_bo_manifest(
                            self.a.dmod.workspace,
                            self.a.args.skip_manifest,
                            self.a.args.only_manifest,
                            repos,
                        )
                    else:
                        if self.a.args.skip_manifest is True:
                            ui.warning(
                                "Cannot skip Deep Manifest if there is no Workspace"
                            )
                        elif self.a.args.only_manifest is True:
                            ui.warning(
                                "Cannot look for Deep Manifest if there is no Workspace"
                            )
                            repos = []
        except Exception as e:
            raise (e)

        return repos

    def _get_data_get_statuses(self) -> Tuple[CollectedStatuses, List[Repo]]:
        if self.a.dmod.workspace:
            status_collector = StatusCollector(self.a.dmod.workspace)
            w_repos = self.a.dmod.workspace.repos
            if self.a.args.skip_manifest is True or self.a.args.only_manifest is True:
                w_repos, _ = self.m_du.filter_repos_bo_manifest(
                    self.a.dmod.workspace,
                    self.a.args.skip_manifest,
                    self.a.args.only_manifest,
                    w_repos,
                )

            if not w_repos:
                raise Exception("Workspace is empty, therefore no valid data")
            ui.info_1(f"Collecting statuses of {len(w_repos)} repo(s)")
            process_items(w_repos, status_collector, num_jobs=self.num_jobs)
            erase_last_line()
            # TODO: we may want to get rid of BareStatus, but there should not be one in any anyway
            return (
                cast(Dict[str, Union[Status, Exception]], status_collector.statuses),
                w_repos,
            )
        return {}, []

    def _get_yaml_data(self) -> None:

        # decided: go Update
        if self.a.dmod.update_source != UpdateSourceEnum.NONE:

            # we need to get ready to Load the YAML file
            y = None  # loaded data

            if self.a.dmod.final_output_path_list.update_on_path:
                with self.a.dmod.final_output_path_list.update_on_path.open(
                    "r"
                ) as opened_file:
                    y = self.yaml.load(opened_file)
            else:
                raise Exception("Cannot obtain Manifest Repo from Workspace to update")

            if y:
                self.yy, self.is_updated = self.m_du.on_update(
                    y,
                    self.mris_h.mris,
                    self.a.dmod.workspace,
                    self.a.dmod.manifest_data_options,
                    self.a.mdo,
                    self.a.gac,
                )

            if not self.yy:
                raise Exception(
                    f"Not able to load YAML data from file: '{self.a.dmod.final_output_path_list.update_on_path}'"  # noqa: E501
                )

        else:  # decided: create Manifest YAML data (not loading YAML data)
            self.yy = self.m_du.do_create(
                self.mris_h.mris, self.a.dmod.manifest_data_options
            )
            if self.yy:
                self.is_updated = True

    """
    ===== 'output_data' section =====
    """

    def output_data(self) -> None:

        if FinalOutputModeFlag.PREVIEW in self.a.dmod.final_output_mode:

            self._output_preview()

            if not self.is_updated or self.is_updated is False:
                ui.warning("There was no change detected")

        else:
            # do not write anything if there is no actual change
            if not self.is_updated or self.is_updated is False:
                ui.warning("Nothing has been changed, skipping")

            else:

                # save data

                self._output_data_ready_save_path()

    def _output_preview(self) -> None:

        # use 'ui.info' instead of real STDOUT
        # this helps tests to catch the output
        buff = io.BytesIO()
        self.yaml.dump(self.yy, buff)
        o_buff = buff.getvalue().decode("utf-8").splitlines(False)
        for x in o_buff:
            ui.info(x)

    def _output_data_ready_save_path(self) -> None:

        message: List[ui.Token] = []
        save_path: Union[Path, None] = None

        first_part: str = ""
        second_part: str = ""

        if FinalOutputModeFlag.NEW in self.a.dmod.final_output_mode:
            save_path = self.a.dmod.get_path_for_new()
            first_part = f"Creating NEW file '{save_path}'"
        elif FinalOutputModeFlag.OVERWRITE in self.a.dmod.final_output_mode:
            save_path = self.a.dmod.get_path_for_new()
            first_part = f"OVERWRITING file '{save_path}'"

        # UPDATE mode can be combined with NEW|OVERWRITE
        if FinalOutputModeFlag.UPDATE in self.a.dmod.final_output_mode:
            # only for UPDATE
            update_path = self.a.dmod.update_source_path
            if update_path:
                update_path = make_relative(update_path)
            save_path = self.a.dmod.get_path_for_update()
            if self.a.dmod.update_source == UpdateSourceEnum.DEEP_MANIFEST:
                second_part = f"UPDATING Deep Manifest on '{update_path}'"
            elif self.a.dmod.update_source == UpdateSourceEnum.FILE:
                second_part = f"UPDATING '{update_path}'"

        if first_part and second_part:
            first_part += " by "

        # take care of printing correct message
        message = [first_part + second_part]
        ui.info_2(*message)

        # take care of obtained save_path
        self._output_data_perform_dump(save_path)

    def _output_data_perform_dump(self, save_path: Union[Path, None]) -> None:

        # we are taking whole data, no constraints are considered.
        if self.m_du.some_remote_is_missing(self.yy) is True:
            ui.warning("This Manifest is not useful due to some missing remotes")

        if save_path:
            with save_path.open("w") as stream:
                self.yaml.dump(self.yy, stream)
            ui.info_1("Dump complete")  # only in this case: report success
        else:
            raise Exception("cannot find the desired path where to write Manifest")
