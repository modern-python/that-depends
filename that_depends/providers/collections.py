import typing

from that_depends.providers.base import AbstractProvider


T = typing.TypeVar("T")


class List(AbstractProvider[T]):
    def __init__(self, *providers: AbstractProvider[T]) -> None:
        self._providers = providers

    async def async_resolve(self) -> list[T]:  # type: ignore[override]
        return [await x.async_resolve() for x in self._providers]

    def sync_resolve(self) -> list[T]:  # type: ignore[override]
        return [x.sync_resolve() for x in self._providers]

    async def __call__(self) -> list[T]:  # type: ignore[override]
        return await self.async_resolve()
