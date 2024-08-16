"""
Groups To Find

Keeps track of what groups was requested
and what groups was found

This can help in a way to have just one class
to transfer data with into the other functions.

And perform easy calculation to see if some
requested group(s) ('self.groups') does not match,
so the exception can be raised properly
"""

from typing import List, Tuple, Union


class GroupsToFind:
    def __init__(self, groups: Union[List[str], None]) -> None:
        self.groups = groups
        self.found_groups: List[str] = []

    def found_some(self) -> bool:
        if self.found_groups:
            return True
        return False

    def found_this(self, this_group: str) -> None:
        """mark single group as found"""
        if self.groups:
            if this_group not in self.found_groups:
                self.found_groups.append(this_group)

    def found_these(self, this_found_groups: List[str]) -> None:
        """mark entire list of groups as found"""
        if self.found_groups:
            # just eliminate duplicates in the list
            self.found_groups = list(set(self.found_groups + this_found_groups))
        else:
            self.found_groups = this_found_groups

    def was_found(self, this_group: str) -> bool:
        """check only single group whether it was found"""
        if this_group in self.found_groups:
            return True
        return False

    def all_found(self) -> Tuple[bool, List[str]]:
        """checks if we have found all groups"""
        if self.groups:
            missing_groups = list(set(self.groups).difference(self.found_groups))
        else:
            return True, []
        if missing_groups:
            return False, missing_groups
        return True, []
