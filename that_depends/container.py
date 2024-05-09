import inspect
import typing

from that_depends.providers import AbstractProvider, AbstractResource, Singleton


if typing.TYPE_CHECKING:
    import typing_extensions


class BaseContainer:
    def __new__(cls, *_: typing.Any, **__: typing.Any) -> "typing_extensions.Self":  # noqa: ANN401
        msg = f"{cls.__name__} should not be instantiated"
        raise RuntimeError(msg)

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
