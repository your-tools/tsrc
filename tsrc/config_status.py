"""
Config Status

Contains all operations and displaying
in regard of config manipulation.

Some atomic config operation can also be found in:
'ConfigTools' class
"""

from typing import List, Optional, Tuple, Union

import cli_ui as ui

from tsrc.config_data import ConfigUpdateData, ConfigUpdateType
from tsrc.config_status_rc import ConfigStatusReturnCode
from tsrc.config_tools import ConfigTools
from tsrc.errors import Error
from tsrc.status_header_dm import StatusHeaderDisplayMode
from tsrc.workspace import Workspace


class ConfigStatus:
    def __init__(
        self,
        workspace: Workspace,
        shdms: List[StatusHeaderDisplayMode],
    ) -> None:
        self.workspace = workspace
        self.shdms = shdms
        """self.shdms: if related markers will not be here,
        nothing will be displayed even when there is some issue"""

    def pre_check_change(
        self,
        cfgud: ConfigUpdateData,
        cfguts: List[ConfigUpdateType],
    ) -> Tuple[List[ConfigStatusReturnCode], List[ConfigUpdateType], bool]:
        cfgrcs: List[ConfigStatusReturnCode] = []
        config_tools = ConfigTools(self.workspace)
        found_some: bool = False  # set to True when there is any chage at all
        for i, this_type in enumerate(cfguts):
            if this_type == ConfigUpdateType.MANIFEST_BRANCH and cfgud.manifest_branch:
                rc = config_tools.update_manifest_branch(cfgud.manifest_branch)
                if rc == ConfigStatusReturnCode.SUCCESS:
                    found_some = True  # marker
                else:
                    if StatusHeaderDisplayMode.BRANCH in self.shdms:
                        # display issue via 'ui'
                        self._manifest_branch_report_issue(rc, cfgud.manifest_branch)

                    no_further_display: bool = False

                    if rc == ConfigStatusReturnCode.REVERT:
                        # in this case, reverting is valid response, thus: SUCCESS
                        rc = ConfigStatusReturnCode.SUCCESS
                        found_some = True  # marker
                        no_further_display = True

                    if rc == ConfigStatusReturnCode.CANCEL:
                        # basicaly mark as not to update
                        cfguts[i] = ConfigUpdateType.NONE
                        no_further_display = True

                    if rc == ConfigStatusReturnCode.NOT_FOUND:
                        # basicaly mark as not to update
                        cfguts[i] = ConfigUpdateType.NONE

                    # skip further display on some cases
                    if no_further_display is True:
                        self._no_further_display(StatusHeaderDisplayMode.BRANCH)

                # finaly add 'rc'
                cfgrcs.append(rc)
        return cfgrcs, cfguts, found_some

    def _no_further_display(
        self,
        mode: StatusHeaderDisplayMode,
    ) -> None:
        """replace given Status Header Display Mode
        by 'NONE', so it will not gets displayed"""
        if mode in self.shdms:
            for index, shdm in enumerate(self.shdms):
                if shdm == mode:
                    self.shdms[index] = StatusHeaderDisplayMode.NONE

    def proceed_to_change(
        self,
        cfgud: ConfigUpdateData,
        cfguts: List[ConfigUpdateType],
    ) -> None:
        config_tools = ConfigTools(self.workspace)
        config_tools.commit_config_update(cfgud, cfguts)

    """display only part"""

    def _manifest_branch_report_issue(
        self, rc: ConfigStatusReturnCode, branch: Optional[str] = None
    ) -> None:
        """report only issue, success will be reported elsewhere,
        everything else will be taken care of elsewhere"""
        if rc == ConfigStatusReturnCode.NOT_FOUND:
            ui.info_2(
                "Such Manifest's branch:",
                ui.green,
                branch,
                ui.reset,
                "was not found on remote,",
                ui.red,
                "ignoring",
                ui.reset,
            )
            raise Error("aborting Manifest branch change")
        if rc == ConfigStatusReturnCode.CANCEL:
            branch_0 = self.workspace.config.manifest_branch_0
            if branch == branch_0:
                ui.info_2(
                    "No change to Manifest's branch, it will still stays on:",
                    ui.green,
                    branch,
                    ui.reset,
                )
            else:
                ui.info_2(
                    "No update, Manifest's branch will still change from:",
                    ui.green,
                    branch_0,
                    ui.reset,
                    "~~>",
                    ui.green,
                    branch,
                    ui.reset,
                )
        if rc == ConfigStatusReturnCode.REVERT:
            ui.info_2(
                "Reverting previous update, Manifest's branch will stays on:",
                ui.green,
                branch,
                ui.reset,
            )

    def manifest_branch_change(self, branch: str, branch_0: Union[str, None]) -> None:
        """report successful change"""
        if branch_0:
            ui.info_2(
                "Accepting Manifest's branch change from:",
                ui.green,
                branch_0,
                ui.reset,
                "~~>",
                ui.green,
                branch,
                ui.reset,
            )
