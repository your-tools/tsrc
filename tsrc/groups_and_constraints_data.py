"""
Dataclass for Groups, 'include_regex', 'exclude_regex'
'singular_remote'

everything that can reduce Repos should have single
place and that place should be here
"""

import argparse
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class GroupsAndConstraints:
    groups: Optional[List[str]] = None  # just what was provided via cmd
    # not to be mistaken with Group class
    singular_remote: str = ""
    include_regex: str = ""
    exclude_regex: str = ""


def get_group_and_constraints_data(args: argparse.Namespace) -> GroupsAndConstraints:

    groups: Optional[List[str]] = None
    if args.groups:
        groups = args.groups
    include_regex: str = ""
    if args.include_regex:
        include_regex = args.include_regex
    exclude_regex: str = ""
    if args.exclude_regex:
        exclude_regex = args.exclude_regex
    return GroupsAndConstraints(
        groups=groups, include_regex=include_regex, exclude_regex=exclude_regex
    )
