"""Support for switch in manifest

'switch' can hold part of new default configuration
and such should only be activated by option '--switch'
when activated:
A) and present:
    it should completely overwrite current configuration.
B) but not present:
    the default (empty) configuration should be used

this is particulary usefull when switching
to new Manifest branch, no need to care about
current configuration anymore.

NOTE: original handling of configuration
should be adhered when no '--switch' is provided
"""

from typing import Any, List, Optional


class Switch:
    def __init__(self, switch_config: Any) -> None:
        self._config: Optional[Any] = None
        self._groups: Optional[List[Any]] = None
        if switch_config:
            self._config = switch_config.get("config")
        if self._config:
            self._groups = self._config.get("groups")
