from typing import Any, Callable, Type


class Marker():

    @classmethod
    def xfail(cls, condition: bool, reason: str) -> Callable: ...


mark = Marker()


def fixture(*args: Any, **kwargs: Any) -> Callable: ...
def raises(error: Type[Exception]) -> Any: ...
