import typing

from that_depends.providers.base import AbstractProvider


T = typing.TypeVar("T")


class List(AbstractProvider[list[T]]):
    def __init__(self, *providers: AbstractProvider[T]) -> None:
        self._providers = providers

    async def async_resolve(self) -> list[T]:
        return [await x.async_resolve() for x in self._providers]

    def sync_resolve(self) -> list[T]:
        return [x.sync_resolve() for x in self._providers]

    async def __call__(self) -> list[T]:
        return await self.async_resolve()


class Dict(AbstractProvider[dict[str, T]]):
    def __init__(self, **providers: AbstractProvider[T]) -> None:
        self._providers = providers

    async def async_resolve(self) -> dict[str, T]:
        return {key: await provider.async_resolve() for key, provider in self._providers.items()}

    def sync_resolve(self) -> dict[str, T]:
        return {key: provider.sync_resolve() for key, provider in self._providers.items()}
