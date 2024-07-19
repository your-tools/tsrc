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
from tsrc.manifest_common_data import ManifestsTypeOfData, get_main_color
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
    ) -> None:
        """this function should be called only once (as only once will work)"""
        if not self._config_update_data:
            self._config_update_data = cfgud
            self._config_update_type = cfguts

            # pre-check all provided updates to config
            cs = ConfigStatus(self.workspace, self.shdms)
            found_some = False
            (
                self._config_status_rc,
                self._config_update_type,
                found_some,
            ) = cs.pre_check_change(cfgud, cfguts)
            if found_some is True:
                self.shdms += [StatusHeaderDisplayMode.CONFIG_CHANGE]

            # do not care if you want to display it, if data are OK, config will be updated
            cs.proceed_to_change(cfgud, self._config_update_type)

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

    def report_collecting(self, c_all: int) -> None:
        """report about how much Repos will be processed
        in order to obatain its Status"""
        c_w_repos = len(self.workspace.repos)
        c_w_repos_s = self._is_plural(c_w_repos, "s")
        c_l_repos = c_all - c_w_repos
        c_l_repos_s = self._is_plural(c_l_repos, "s")
        c_all_es = self._is_plural(c_w_repos + c_l_repos, "es")

        if c_w_repos == c_all:  # no leftover repo(s)
            ui.info_1(
                f"Collecting status{c_all_es} of {c_w_repos} workspace repo{c_w_repos_s}"
            )
        else:  # with leftover repo(s)
            if c_w_repos == 0:  # without workspace repo(s)
                ui.info_1(
                    f"Collecting status{c_all_es} of {c_l_repos} leftover repo{c_l_repos_s}"  # noqa: E501
                )
            else:  # combined workspace and leftover repo(s)
                ui.info_1(
                    f"Collecting status{c_all_es} of {c_w_repos} workspace repo{c_w_repos_s} + {c_l_repos} leftover repo{c_l_repos_s}"  # noqa: E501
                )

    """ internal functions """

    def _is_plural(self, value: int, ext: str) -> str:
        """return plural defined by 'ext' when value > 1"""
        if value > 1:
            return ext
        return ""

    def _header_manifest_url(self, url: str) -> None:
        ui.info_1(
            "Manifest's URL:", get_main_color(ManifestsTypeOfData.DEEP), url, ui.reset
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
