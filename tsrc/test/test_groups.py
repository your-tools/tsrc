import pytest

from tsrc.groups import GroupList, GroupNotFound, UnknownGroupElement


def test_happy_grouping() -> None:
    group_list = GroupList(elements=["a", "b", "c"])
    group_list.add("default", ["a", "b"])
    group_list.add("other", ["c"], includes=["default"])
    actual = group_list.get_elements(groups=["other"])
    assert actual == ["a", "b", "c"]


def test_remove_duplicates() -> None:
    group_list = GroupList(elements=["a", "b", "c", "z"])
    group_list.add("one", ["a", "z"])
    group_list.add("two", ["b", "z"])
    group_list.add("all", ["c"], includes=["one", "two"])
    actual = group_list.get_elements(groups=["all"])
    assert actual == ["a", "z", "b", "c"]


def test_unknown_element() -> None:
    group_list = GroupList(elements=["a", "b", "c"])
    with pytest.raises(UnknownGroupElement) as e:
        group_list.add("invalid-group", ["no-such-element"])
    assert e.value.group_name == "invalid-group"
    assert e.value.element == "no-such-element"


def test_unknown_include() -> None:
    group_list = GroupList(elements=["a", "b", "c"])
    group_list.add("default", ["a", "b"])
    group_list.add("invalid-group", ["c"], includes=["no-such-group"])
    with pytest.raises(GroupNotFound) as e:
        group_list.get_elements(groups=["invalid-group"])
    assert e.value.parent_group is not None
    assert e.value.parent_group.name == "invalid-group"
    assert e.value.group_name == "no-such-group"


def test_diamond() -> None:
    group_list = GroupList(elements=["a", "b", "c", "d"])
    group_list.add("top", ["a"])
    group_list.add("left", ["b"], includes=["top"])
    group_list.add("right", ["c"], includes=["top"])
    group_list.add("bottom", ["d"], includes=["left", "right"])
    actual = group_list.get_elements(groups=["bottom"])
    assert actual == ["a", "b", "c", "d"]


def test_ping_pong() -> None:
    group_list = GroupList(elements=["a", "b"])
    group_list.add("ping", ["a"], includes=["pong"])
    group_list.add("pong", ["b"], includes=["ping"])
    actual = group_list.get_elements(groups=["ping"])
    assert actual == ["b", "a"]


def test_circle() -> None:
    group_list = GroupList(elements=["a", "b", "c"])
    group_list.add("a", ["a"], includes=["b"])
    group_list.add("b", ["b"], includes=["c"])
    group_list.add("c", ["c"], includes=["a"])
    actual = group_list.get_elements(groups=["a"])
    assert actual == ["c", "b", "a"]


def test_unknown_group() -> None:
    group_list = GroupList(elements=["a", "b", "c"])
    group_list.add("default", ["a", "b"])
    with pytest.raises(GroupNotFound) as e:
        group_list.get_elements(groups=["no-such-group"])
    assert e.value.parent_group is None
    assert e.value.group_name == "no-such-group"
