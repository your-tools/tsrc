"""Status Header Display Mode"""

from enum import Flag


class StatusHeaderDisplayMode(Flag):
    NONE = 0
    URL = 1
    BRANCH = 2
    CONFIG_CHANGE = 4
    """CONFIG_CHAGE: this flag should be set automatically,
    upon successful call for change in config."""
