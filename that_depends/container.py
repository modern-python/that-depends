import inspect
import typing

from that_depends.providers import AbstractProvider, AbstractResource, Singleton


if typing.TYPE_CHECKING:
    import typing_extensions


class BaseContainer:
    def __new__(cls, *_: typing.Any, **__: typing.Any) -> "typing_extensions.Self":  # noqa: ANN401
        raise RuntimeError("%s should not be instantiated" % cls.__name__)

    @classmethod
    async def tear_down(cls) -> None:
        for _k, v in inspect.getmembers(cls):
            if isinstance(v, AbstractResource | Singleton):
                await v.tear_down()

    @classmethod
    def reset_override(cls) -> None:
        for _k, v in inspect.getmembers(cls):
            if isinstance(v, AbstractProvider):
                v.reset_override()
