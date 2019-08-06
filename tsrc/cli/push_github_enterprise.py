import tsrc.cli.push_github
import argparse
from typing import Optional

from github3 import GitHub

import tsrc
import tsrc.github
from tsrc.cli.push import RepositoryInfo


class PushAction(tsrc.cli.push_github.PushAction):
    def __init__(
        self,
        repository_info: RepositoryInfo,
        args: argparse.Namespace,
        github_api: Optional[GitHub] = None,
    ) -> None:
        if not github_api:
            github_api = tsrc.github.login(
                github_enterprise_url=repository_info.repository_login_url
            )

        super().__init__(repository_info, args, github_api)
