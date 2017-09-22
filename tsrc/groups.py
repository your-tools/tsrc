""" Support for finding elements inside a list of groups """

import tsrc


class GroupError(tsrc.Error):
    pass


class GroupNotFound(GroupError):
    def __init__(self, group_name, parent_group=None):
        self.group_name = group_name
        self.parent_group = parent_group
        if self.parent_group:
            message = "Invalid include detected for %s:\n" % self.parent_group.name
        else:
            message = ""
        message += "No such group: %s" % self.group_name
        super().__init__(message)


class UnknownElement(GroupError):
    def __init__(self, group_name, element):
        self.group_name = group_name
        self.element = element
        message = "%s: unknown element: %s" % (group_name, element)
        super().__init__(message)


# pylint: disable=too-few-public-methods
class Group:
    def __init__(self, name, elements, includes=None):
        self.name = name
        self.elements = elements
        self.includes = includes or list()


class GroupList:
    def __init__(self, *, elements):
        self.groups = dict()
        self.all_elements = elements
        self._groups_seen = set()

    def add(self, name, elements, includes=None):
        for element in elements:
            if element not in self.all_elements:
                raise UnknownElement(name, element)
        self.groups[name] = Group(name, elements, includes=includes)

    def get_group(self, name):
        return self.groups.get(name)

    def get_elements(self, groups=None):
        self._groups_seen = set()
        res = set()
        if not groups:
            return self.all_elements
        self._rec_get_elements(res, groups, parent_group=None)
        return res

    def _rec_get_elements(self, res, group_names, *, parent_group):
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
