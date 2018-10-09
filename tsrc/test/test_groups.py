import tsrc

import pytest


def test_happy_grouping() -> None:
    group_list = tsrc.GroupList(elements={"a", "b", "b", "c"})
    group_list.add("default", {"a", "b"})
    group_list.add("other", {"c"}, includes=["default"])
    actual = group_list.get_elements(groups=["other"])
    assert actual == {"a", "b", "c"}


def test_default_is_all() -> None:
    group_list = tsrc.GroupList(elements={"a", "b", "c"})
    assert group_list.get_elements() == {"a", "b", "c"}


def test_unknown_element() -> None:
    group_list = tsrc.GroupList(elements={"a", "b", "c"})
    with pytest.raises(tsrc.UnknownGroupElement) as e:
        group_list.add("invalid-group", {"no-such-element"})
    assert e.value.group_name == "invalid-group"
    assert e.value.element == "no-such-element"


def test_unknown_include() -> None:
    group_list = tsrc.GroupList(elements={"a", "b", "c"})
    group_list.add("default", {"a", "b"})
    group_list.add("invalid-group", {"c"}, includes=["no-such-group"])
    with pytest.raises(tsrc.GroupNotFound) as e:
        group_list.get_elements(groups=["invalid-group"])
    assert e.value.parent_group.name == "invalid-group"
    assert e.value.group_name == "no-such-group"


def test_diamond() -> None:
    group_list = tsrc.GroupList(elements={"a", "b", "c", "d"})
    group_list.add("top", {"a"})
    group_list.add("left", {"b"}, includes=["top"])
    group_list.add("right", {"c"}, includes=["top"])
    group_list.add("bottom", {"d"}, includes=["left", "right"])
    actual = group_list.get_elements(groups=["bottom"])
    assert actual == {"a", "b", "c", "d"}


def test_ping_pong() -> None:
    group_list = tsrc.GroupList(elements={"a", "b"})
    group_list.add("ping", {"a"}, includes=["pong"])
    group_list.add("pong", {"b"}, includes=["ping"])
    actual = group_list.get_elements(groups=["ping"])
    assert actual == {"a", "b"}


def test_circle() -> None:
    group_list = tsrc.GroupList(elements={"a", "b", "c"})
    group_list.add("a", {"a"}, includes=["b"])
    group_list.add("b", {"b"}, includes=["c"])
    group_list.add("c", {"c"}, includes=["a"])
    actual = group_list.get_elements(groups=["a"])
    assert actual == {"a", "b", "c"}


def test_unknown_group() -> None:
    group_list = tsrc.GroupList(elements={"a", "b", "c"})
    group_list.add("default", {"a", "b"})
    with pytest.raises(tsrc.GroupNotFound) as e:
        group_list.get_elements(groups=["no-such-group"])
    assert e.value.parent_group is None
    assert e.value.group_name == "no-such-group"
