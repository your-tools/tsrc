import textwrap

import tsrc.config


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
    config = tsrc.config.read(config_path=tsrc_yml_path)
    assert config["auth"]["gitlab"]["token"] == "MY_SECRET_TOKEN"
