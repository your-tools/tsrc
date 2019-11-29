""" Support for finding elements inside a list of groups """

from typing import Any, Dict, Generic, Iterable, List, Optional, Set, TypeVar  # noqa
import tsrc

T = TypeVar("T")


class GroupError(tsrc.Error):
    pass


class Group(Generic[T]):
    def __init__(
        self, name: str, elements: Iterable[T], includes: Optional[List[str]] = None
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
            message = "Invalid include detected for %s:\n" % self.parent_group.name
        else:
            message = ""
        message += "No such group: %s" % self.group_name
        super().__init__(message)


class UnknownElement(GroupError):
    def __init__(self, group_name: str, element: T) -> None:
        self.group_name = group_name
        self.element = element
        message = "%s: unknown element: %s" % (group_name, element)
        super().__init__(message)


class GroupList(Generic[T]):
    def __init__(self, *, elements: Iterable[T]) -> None:
        self.groups = {}  # type: Dict[str, Group[T]]
        self.all_elements = elements
        self._groups_seen = set()  # type: Set[str]

    def add(
        self, name: str, elements: Iterable[T], includes: Optional[List[str]] = None
    ) -> None:
        for element in elements:
            if element not in self.all_elements:
                raise UnknownElement(name, element)
        self.groups[name] = Group(name, elements, includes=includes)

    def get_group(self, name: str) -> Optional[Group[T]]:
        return self.groups.get(name)

    def get_elements(self, groups: List[str]) -> Iterable[T]:
        self._groups_seen = set()
        res = set()  # type: Set[T]
        self._rec_get_elements(res, groups, parent_group=None)
        return res

    def _rec_get_elements(
        self, res: Set[T], group_names: List[str], *, parent_group: Optional[Group[T]]
    ) -> None:
        for group_name in group_names:
            if group_name in self._groups_seen:
                return
            if group_name not in self.groups:
                raise GroupNotFound(group_name, parent_group=parent_group)
            group = self.groups[group_name]
            for element in group.elements:
                res.add(element)
            self._groups_seen.add(group.name)
            self._rec_get_elements(res, group.includes, parent_group=group)
