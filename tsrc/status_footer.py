"""Status Footer:
obtains data via OverallWRStat from WorkspaceReposSummary
and print it in dependance of usecase.
Current usecases are:
* 'cli/status.py' - prints footnote information,
    that will start with hard continuous line (resembles footnote)
    which can be in form of several lines (in relation to status)
* 'manifest.py' - prints just simple information,
    in rare cases there will be up to 2 lines
"""

from typing import List

import cli_ui as ui

from tsrc.overall_w_r_stat import OverallWRStat, StatusFooterUseCaseMode


class StatusFooter:
    def __init__(
        self,
        owrs: OverallWRStat,
    ) -> None:
        self.owrs = owrs

    def report(self) -> None:
        """prints current footer"""
        print("DEBUG: TODO: StatusFooter reports from here")

        # check if repo is ready
        if (
            isinstance(self.owrs.is_manifest_repo_ready, bool)
            and self.owrs.is_manifest_repo_ready is False  # noqa: W503
        ):
            self._uip_manifest_repo_not_ready
            return

        # check if Manifest branch is going to change
        if (
            isinstance(self.owrs.manifest_branch_change, bool)
            and self.owrs.manifest_branch_change is True  # noqa: W503
        ):
            self._uip_branch_will_change_after_sync()

        print("DEBUG: TODO: at the and of StatusFooter")

    def _uip_manifest_repo_not_ready(self) -> None:
        if self.owrs.mode == StatusFooterUseCaseMode.MANIFEST:
            ui.info_2("Clean Manifest repository before calling 'sync'")

    def _uip_branch_will_change_after_sync(self) -> None:
        if self.owrs.mode == StatusFooterUseCaseMode.MANIFEST:
            message = [
                "Currently configured branch on next 'sync':",
                ui.red,
                "(will change)",
            ]
            if isinstance(self.owrs.manifest_branch_change_from, str):
                message += [
                    ui.reset,
                    "from:",
                    ui.green,
                    self.owrs.manifest_branch_change_from,
                ]
            else:
                message += [ui.reset, "from:", ui.green, self.owrs.manifest_branch_0]
            message += [
                ui.reset,
                "to:",
                ui.green,
                self.owrs.manifest_branch,
                ui.reset,
            ]
            ui.info_2(*message)

    # TODO: adjust to new class
    def _make_footnote_line(self, message: List[str]) -> str:
        """Return footer line that is adjusted to cover the full line"""
        msg_header = ""
        tmp_len = 0
        for le in range(len(message)):
            if not isinstance(message[le], type(ui.reset)):
                tmp_len = int(tmp_len) + len(str(message[le])) + 1
        for _ in range(int(tmp_len)):
            msg_header = "{}{}".format(msg_header, "_")
        return msg_header
