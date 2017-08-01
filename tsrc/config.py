""" Parse tsrc config files """

import xdg

import path
import ruamel.yaml


def read(config_path=None):
    if not config_path:
        config_path = path.Path(xdg.XDG_CONFIG_HOME)
        config_path = config_path.joinpath("tsrc.yml")
    return ruamel.yaml.safe_load(config_path.text())
