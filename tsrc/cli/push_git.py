""" Ability to push to a standard Git system without requiring Github or Gitlab.
    No pull requests will be automatically created. """

import argparse
import tsrc.git
from tsrc.cli.push import RepositoryInfo


class PushAction(tsrc.cli.push.PushAction):
    def __init__(
        self, repository_info: RepositoryInfo, args: argparse.Namespace
    ) -> None:
        super().__init__(repository_info, args)

    def setup_service(self) -> None:
        pass

    def post_push(self) -> None:
        pass
