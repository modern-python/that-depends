import typing

from that_depends.providers.base import AbstractProvider


T = typing.TypeVar("T")


class List(AbstractProvider[T]):
    def __init__(self, *providers: AbstractProvider[T]) -> None:
        self._providers = providers

    async def resolve(self) -> list[T]:  # type: ignore[override]
        return [await x.resolve() for x in self._providers]

    async def __call__(self) -> list[T]:  # type: ignore[override]
        return await self.resolve()
