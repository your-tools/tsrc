"""Status Header

normalize header printout for every descriptive commands, like:
* status
* manifest

What it does:
Prints (implemented) configured details
as per request (see StatusHeaderDisplayMode)
Currently implemented:
* Manifest's branch (full report, even on change)
* Manifest's URL
"""

from typing import List, Union

import cli_ui as ui

# from enum import Enum
from tsrc.config_data import ConfigUpdateData, ConfigUpdateType
from tsrc.config_status import ConfigStatus

# import tsrc.config_status_rc
from tsrc.config_status_rc import ConfigStatusReturnCode
from tsrc.errors import Error
from tsrc.manifest_common_data import ManifestsTypeOfData, mtod_get_main_color
from tsrc.status_header_dm import StatusHeaderDisplayMode
from tsrc.workspace import Workspace


class StatusHeader:
    def __init__(
        self,
        workspace: Workspace,
        shdms: List[StatusHeaderDisplayMode],
    ) -> None:
        self.workspace = workspace
        self.branch = workspace.config.manifest_branch
        self.branch_0 = workspace.config.manifest_branch_0
        self.url = workspace.config.manifest_url

        # internal variable
        self.shdms = shdms

        # internal marker
        self._config_change: bool = False

        # optial variables
        self._config_update_data: Union[ConfigUpdateData, None] = None
        self._config_update_type: List[ConfigUpdateType] = []
        self._config_status_rc: List[ConfigStatusReturnCode] = []

    def register_change(
        self,
        cfgud: ConfigUpdateData,
        cfguts: List[ConfigUpdateType],
    ) -> bool:
        """this function should be called only once (as only once will work)"""
        if not self._config_update_data:
            self._config_update_data = cfgud
            self._config_update_type = cfguts

            # pre-check all provided updates to config
            cs = ConfigStatus(self.workspace, self.shdms)
            try:
                found_some = False
                (
                    self._config_status_rc,
                    self._config_update_type,
                    found_some,
                ) = cs.pre_check_change(cfgud, cfguts)
            except Error as e:
                ui.error(e)
                return False
            else:
                if found_some is True:
                    self.shdms += [StatusHeaderDisplayMode.CONFIG_CHANGE]

                # do not care if you want to display it, if data are OK, config will be updated
                cs.proceed_to_change(cfgud, self._config_update_type)
        return True

    def display(self) -> None:
        if StatusHeaderDisplayMode.CONFIG_CHANGE in self.shdms:
            """always check for this flag first, as it may introduce change
            and such change may require pre-check and if that fails,
            report may need to be produced"""
            if self._config_update_type:
                self._config_change = True
        for shdm in self.shdms:
            if StatusHeaderDisplayMode.URL in shdm:
                self._header_manifest_url(self.url)
            if StatusHeaderDisplayMode.BRANCH in shdm:
                if (
                    self._config_update_data
                    and self._config_update_data.manifest_branch  # noqa: W503
                    and ConfigUpdateType.MANIFEST_BRANCH  # noqa: W503
                    in self._config_update_type  # noqa: W503
                ):
                    self._header_manifest_branch(
                        self._config_update_data.manifest_branch, self.branch_0
                    )
                else:
                    self._header_manifest_branch(self.branch, self.branch_0)

    def report_collecting(self, cw: int, cl: int = 0, cb: int = 0) -> None:
        """
        Properly display counters of Repos of various kind,
        that will be processed together, like:
        * 'cw' - count of Workspace Repos
        * 'cl' - count of leftovers Repo (both DM and FM)
        * 'cb' - count of temporary Bare Repos (both DM and FM)
        """
        cw_pl = self._is_plural(cw, "s")
        cl_pl = self._is_plural(cl, "s")
        cb_pl = self._is_plural(cb, "s")
        str_cw = f"{cw} workspace repo{cw_pl}"
        str_cl = f"{cl} leftovers repo{cl_pl}"
        str_cb = f"{cb} tmp bare repo{cb_pl}"
        start_pl = ""
        if cw > 0:
            start_pl = self._is_plural(cw, "es")
        elif cl > 0:
            start_pl = self._is_plural(cl, "es")
        else:
            start_pl = self._is_plural(cb, "es")

        str_out = ""
        if cw > 0 or cl > 0 or cb > 0:
            str_out = f"Collecting status{start_pl} of "
        if cw > 0:
            str_out += str_cw
            if cl > 0 or cb > 0:
                str_out += " + "
        if cl > 0:
            str_out += str_cl
            if cb > 0:
                str_out += " + "
        if cb > 0:
            str_out += str_cb

        if str_out:
            ui.info_1(str_out)

    """ internal functions """

    def _is_plural(self, value: int, ext: str) -> str:
        """return plural defined by 'ext' when value > 1"""
        if value > 1:
            return ext
        return ""

    def _header_manifest_url(self, url: str) -> None:
        ui.info_1(
            "Manifest's URL:",
            mtod_get_main_color(ManifestsTypeOfData.DEEP),
            url,
            ui.reset,
        )

    def _header_manifest_branch(
        self,
        branch: str,
        branch_0: Union[str, None],
    ) -> None:
        if self._config_change is True:
            cs = ConfigStatus(self.workspace, self.shdms)
            cs.manifest_branch_change(branch, branch_0)
        else:
            self._header_manifest_branch_nc(branch, branch_0)
            pass

    def _header_manifest_branch_nc(
        self,
        branch: str,
        branch_0: Union[str, None],
    ) -> None:
        if branch == branch_0:
            ui.info_1("Manifest's branch:", ui.green, branch, ui.reset)
        else:
            ui.info_1(
                "Manifest's branch will change from:",
                ui.green,
                branch_0,
                ui.reset,
                "~~>",
                ui.green,
                branch,
            )
