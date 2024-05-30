"""
Status Header Display Mode

Keeps information about what data can be displayed
in the status header of some commands

Currently it is implemented into:
* status
* manifest
"""

from enum import Flag


class StatusHeaderDisplayMode(Flag):
    NONE = 0
    URL = 1
    BRANCH = 2
    CONFIG_CHANGE = 4
    """CONFIG_CHAGE: this flag should be set automatically,
    upon successful call for change in config."""
