import ruamel.yaml
import textwrap

import schema
from path import Path

import tsrc

import pytest
import mock


def test_read_config(tmp_path: Path) -> None:
    tsrc_yml_path = tmp_path / "tsrc.yml"
    tsrc_yml_path.write_text(
        textwrap.dedent(
            """\
            auth:
              gitlab:
                token: MY_SECRET_TOKEN
            """)
    )
    config = tsrc.parse_tsrc_config(config_path=tsrc_yml_path)
    assert config["auth"]["gitlab"]["token"] == "MY_SECRET_TOKEN"


def test_invalid_syntax(tmp_path: Path) -> None:
    foo_yml = tmp_path / "foo.yml"
    foo_yml.write_text(textwrap.dedent(
        """
        foo:
          bar:
            baz: [

        baz: 42
        """))
    with pytest.raises(tsrc.InvalidConfig) as e:
        dummy_schema = mock.Mock()
        tsrc.parse_config(foo_yml, dummy_schema)
    raised_error = e.value
    assert raised_error.config_path == foo_yml
    assert isinstance(raised_error.cause, ruamel.yaml.error.YAMLError)


def test_invalid_schema(tmp_path: Path) -> None:
    foo_yml = tmp_path / "foo.yml"
    foo_yml.write_text(textwrap.dedent(
        """
        foo:
            bar: 42
        """
    ))
    foo_schema = schema.Schema(
        {"foo": {"bar": str}}
    )
    with pytest.raises(tsrc.InvalidConfig) as e:
        tsrc.parse_config(foo_yml, foo_schema)
    assert isinstance(e.value.cause, schema.SchemaError)


def test_roundtrip(tmp_path: Path) -> None:
    foo_yml = tmp_path / "foo.yml"
    contents = textwrap.dedent(
        """\
        # important comment
        foo: 0
        """
    )
    foo_yml.write_text(contents)
    foo_schema = schema.Schema({"foo": int})
    parsed = tsrc.parse_config(foo_yml, foo_schema, roundtrip=True)

    parsed["foo"] = 42
    tsrc.dump_config(parsed, foo_yml)
    actual = foo_yml.text()
    expected = contents.replace("0", "42")
    assert actual == expected


def test_use_pure_python_types_when_not_roundtripping(tmp_path: Path) -> None:
    foo_yml = tmp_path / "foo.yml"
    foo_yml.write_text("foo: 42\n")
    foo_schema = schema.Schema({"foo": int})
    parsed = tsrc.parse_config(foo_yml, foo_schema, roundtrip=False)
    # Usually it's bad to compare types directly, and isinstance()
    # should be used instead. But here we want to assert we have
    # a proper dict, and not an OrderedDict or a yaml's CommentedMap
    assert type(parsed) == type(dict())   # noqa
