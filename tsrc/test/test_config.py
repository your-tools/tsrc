import textwrap

import schema

import tsrc.config

import pytest
import mock


def test_read_config(tmp_path):
    tsrc_yml_path = tmp_path.joinpath("tsrc.yml")
    tsrc_yml_path.write_text(
        textwrap.dedent(
            """\
            auth:
              gitlab:
                token: MY_SECRET_TOKEN
            """)
    )
    config = tsrc.config.parse_tsrc_config(config_path=tsrc_yml_path)
    assert config["auth"]["gitlab"]["token"] == "MY_SECRET_TOKEN"


def test_invalid_syntax(tmp_path):
    foo_yml = tmp_path.joinpath("foo.yml")
    foo_yml.write_text(textwrap.dedent(
        """
        foo:
          bar:
            baz: [

        baz: 42
        """))
    with pytest.raises(tsrc.InvalidConfig) as e:
        dummy_schema = mock.Mock()
        tsrc.config.parse_config_file(foo_yml, dummy_schema)
    assert e.value.path == foo_yml
    assert "flow sequence" in e.value.details
    assert "ligne 3, col 9" in e.value.details


def test_invalid_schema(tmp_path):
    foo_yml = tmp_path.joinpath("foo.yml")
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
        tsrc.config.parse_config_file(foo_yml, foo_schema)
    assert "42 should be instance of 'str'" in e.value.details
