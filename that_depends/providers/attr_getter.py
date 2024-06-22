import typing

from that_depends.providers.base import AbstractProvider


T = typing.TypeVar("T")
P = typing.ParamSpec("P")


class AttrGetter(AbstractProvider[T]):
    __slots__ = "_provider", "_attr_name"

    def __init__(self, provider: AbstractProvider[T], attr_name: str) -> None:
        self._provider = provider
        self._attr_name = attr_name

    async def async_resolve(self) -> typing.Any:  # noqa: ANN401
        return getattr(await self._provider.async_resolve(), self._attr_name)

    def sync_resolve(self) -> typing.Any:  # noqa: ANN401
        return getattr(self._provider.sync_resolve(), self._attr_name)
