"""
Config Tools

Contains all config-change related functions
that can be performed on config

The idea is to reach full command control
of the config, so no manual editing needs to be performed

Functions of this class should return only 'bool'
and/or relevant data. It should not display anything anywhere
"""

from typing import List

from tsrc.config_data import ConfigUpdateData, ConfigUpdateType
from tsrc.config_status_rc import ConfigStatusReturnCode
from tsrc.git_remote import remote_branch_exist
from tsrc.workspace import Workspace


class ConfigTools:
    def __init__(
        self,
        workspace: Workspace,
    ) -> None:
        self.workspace = workspace

    def commit_config_update(
        self,
        cfgud: ConfigUpdateData,
        cfguts: List[ConfigUpdateType],
    ) -> None:
        """once all updates are done,
        calling commit is in order"""

        for this_type in cfguts:
            if this_type == ConfigUpdateType.MANIFEST_BRANCH and cfgud.manifest_branch:
                self.workspace.config.manifest_branch = cfgud.manifest_branch
            # here add more type match option when implemented

        # now write to config (all changes at once)
        self.workspace.config.save_to_file(self.workspace.cfg_path)

    def update_manifest_branch(
        self,
        new_branch: str,
    ) -> ConfigStatusReturnCode:
        if self.workspace.config.manifest_branch == new_branch:
            return ConfigStatusReturnCode.CANCEL

        if self.workspace.config.manifest_branch_0 != new_branch:
            rc_is_on_remote = remote_branch_exist(
                self.workspace.config.manifest_url,
                new_branch,
            )
            if rc_is_on_remote == 0:
                return ConfigStatusReturnCode.SUCCESS
            else:
                return ConfigStatusReturnCode.NOT_FOUND
        else:
            return ConfigStatusReturnCode.REVERT

    def local_update_manifest_branch(self) -> None:
        """
        Q: Why we should not accept
        manifest branch change to branch that does not
        exists remotely, but it is only in local
        (Workspace) Manifest's repository?
        A: because Future Manifest will not work in such case.
        Q: What about Deep Manifest?
        A: Deep Manifest will work when we chage branch
        of Manifest repo by 'git' command.
        Deep Manifest does not care about configured branch
        """
        pass
