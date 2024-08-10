import typing
from collections.abc import Collection

from that_depends.providers.base import AbstractProvider


T = typing.TypeVar("T")
P = typing.ParamSpec("P")


class Object(AbstractProvider[T]):
    __slots__ = ("_obj",)

    def __init__(self, obj: T) -> None:
        self._obj = obj

    async def async_resolve(self) -> T:
        return self._obj

    def sync_resolve(self) -> T:
        return self._obj

    @property
    def dependencies(self) -> Collection[AbstractProvider[typing.Any]]:
        return []
