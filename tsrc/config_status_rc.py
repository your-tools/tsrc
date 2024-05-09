"""Config Status Return Code

When change is registered to some configuration item,
it does not mean, that there will not be any issue.

Here is some common Enums of what can be used
as return code. Extend it to your liking.
"""

from enum import Enum, unique


@unique
class ConfigStatusReturnCode(Enum):
    SUCCESS = 0
    IGNORE = 1
    CANCEL = 2
    NOT_FOUND = 3
    REVERT = 4
    ERROR = 5
