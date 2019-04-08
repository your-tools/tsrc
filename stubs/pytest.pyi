from typing import Any, Callable, Type, NoReturn


class Marker():

    @classmethod
    def xfail(cls, condition: bool, reason: str) -> Callable[..., Any]: ...


mark = Marker()


def fixture(*args: Any, **kwargs: Any) -> Callable[..., Any]: ...
def raises(error: Type[Exception]) -> Any: ...
def fail(message: str) -> NoReturn: ...
