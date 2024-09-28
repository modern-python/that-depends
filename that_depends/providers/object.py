import typing

from that_depends.providers.base import AbstractProvider


T = typing.TypeVar("T")
P = typing.ParamSpec("P")


class Object(AbstractProvider[T]):
    __slots__ = ("_obj",)

    def __init__(self, obj: T) -> None:
        super().__init__()
        self._obj: typing.Final = obj

    async def async_resolve(self) -> T:
        return self._obj

    def sync_resolve(self) -> T:
        return self._obj
