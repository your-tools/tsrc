""" Support for groups of elements """
# Note that groups are allowed to include other groups.

from typing import Any, Dict, Generic, List, Optional, TypeVar

from tsrc.errors import Error

T = TypeVar("T")


class GroupError(Error):
    pass


class Group(Generic[T]):
    def __init__(
        self, name: str, elements: List[T], includes: Optional[List[str]] = None
    ) -> None:
        self.name = name
        self.elements = elements
        self.includes = includes or []


class GroupNotFound(GroupError):
    def __init__(
        self, group_name: str, parent_group: Optional[Group[Any]] = None
    ) -> None:
        self.group_name = group_name
        self.parent_group = parent_group
        if self.parent_group:
            message = f"Invalid include detected for '{self.parent_group.name}':\n"
        else:
            message = ""
        message += f"No such group: '{self.group_name}'"
        super().__init__(message)


class UnknownGroupElement(GroupError):
    def __init__(self, group_name: str, element: T) -> None:
        self.group_name = group_name
        self.element = element
        message = f"group '{group_name}': unknown element: '{element}'"
        super().__init__(message)


class GroupList(Generic[T]):
    """Usage:

    >>> group_list = GroupList()
    >>> group_list.add("group1", ["foo", "bar"])
    >>> group_list.add("group2", ["spam"], includes=["group"])
    >>> elements = group_list.get_elements(groups=["group2"])
    ["spam", "foo", "bar"]

    """

    def __init__(self, *, elements: List[T]) -> None:
        self.groups: Dict[str, Group[T]] = {}
        self.all_elements = elements
        self._groups_seen: List[str] = []

    def add(
        self, name: str, elements: List[T], includes: Optional[List[str]] = None
    ) -> None:
        for element in elements:
            if element not in self.all_elements:
                raise UnknownGroupElement(name, element)
        self.groups[name] = Group(name, elements, includes=includes)

    def get_group(self, name: str) -> Optional[Group[T]]:
        return self.groups.get(name)

    def get_elements(self, groups: List[str]) -> List[T]:
        # Note: to get all elements in a group, recursively parse
        # the groups and their includes, while making sure no
        # group is processed twice.
        #
        # This algorithms allows to have groups that include each other
        # without creating infinite loops.
        self._groups_seen = []
        # Note: we need to keep the result free of duplicates *and*
        # in the correct order.
        # There's no OrderedSet in the stdlib, so we use a dict instead
        # where keys don't matter
        res: Dict[T, bool] = {}
        self._rec_get_elements(res, groups, parent_group=None)
        return list(res.keys())

    def _rec_get_elements(
        self,
        res: Dict[T, bool],
        group_names: List[str],
        *,
        parent_group: Optional[Group[T]],
    ) -> None:
        for group_name in group_names:
            if group_name in self._groups_seen:
                return
            if group_name not in self.groups:
                raise GroupNotFound(group_name, parent_group=parent_group)
            group = self.groups[group_name]
            self._groups_seen.append(group.name)
            self._rec_get_elements(res, group.includes, parent_group=group)
            for element in group.elements:
                res[element] = True
