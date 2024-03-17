import typing


class BaseContainer:
    def __new__(cls, *_: typing.Any, **__: typing.Any) -> typing.Self:  # noqa: ANN401
        raise RuntimeError("%s should not be instantiated" % cls.__name__)
