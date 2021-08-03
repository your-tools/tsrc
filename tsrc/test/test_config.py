import textwrap
from pathlib import Path

import mock
import pytest
import ruamel.yaml
import schema

from tsrc.config import parse_config
from tsrc.errors import InvalidConfig


def test_invalid_syntax(tmp_path: Path) -> None:
    foo_yml = tmp_path / "foo.yml"
    foo_yml.write_text(
        textwrap.dedent(
            """
        foo:
          bar:
            baz: [

        baz: 42
        """
        )
    )
    with pytest.raises(InvalidConfig) as e:
        dummy_schema = mock.Mock()
        parse_config(foo_yml, schema=dummy_schema)
    raised_error = e.value
    assert raised_error.config_path == foo_yml
    assert isinstance(raised_error.cause, ruamel.yaml.error.YAMLError)


def test_invalid_schema(tmp_path: Path) -> None:
    foo_yml = tmp_path / "foo.yml"
    foo_yml.write_text(
        textwrap.dedent(
            """
        foo:
            bar: 42
        """
        )
    )
    foo_schema = schema.Schema({"foo": {"bar": str}})
    with pytest.raises(InvalidConfig) as e:
        parse_config(foo_yml, schema=foo_schema)
    assert isinstance(e.value.cause, schema.SchemaError)


def test_use_pure_python_types(tmp_path: Path) -> None:
    """Check that parse_config() returns pure Python dicts,
    not an OrderedDict or yaml's CommentedMap
    """
    foo_yml = tmp_path / "foo.yml"
    foo_yml.write_text("foo: 42\n")
    foo_schema = schema.Schema({"foo": int})
    parsed = parse_config(foo_yml, schema=foo_schema)
    assert parsed.__class__ == dict
