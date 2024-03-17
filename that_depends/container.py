import inspect
import typing

from that_depends.providers import AbstractProvider, AbstractResource


class BaseContainer:
    def __new__(cls, *_: typing.Any, **__: typing.Any) -> typing.Self:  # noqa: ANN401
        raise RuntimeError("%s should not be instantiated" % cls.__name__)

    @classmethod
    async def tear_down(cls) -> None:
        for _k, v in inspect.getmembers(cls):
            if isinstance(v, AbstractResource):
                await v.tear_down()

    @classmethod
    def reset_override(cls) -> None:
        for _k, v in inspect.getmembers(cls):
            if isinstance(v, AbstractProvider):
                v.reset_override()
