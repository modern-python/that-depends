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


class Selector(AbstractProvider[T]):
    def __init__(self, selector: typing.Callable[[], str], **providers: AbstractProvider[T]) -> None:
        self._selector = selector
        self._providers = providers

    async def async_resolve(self) -> T:
        selected_key = self._selector()
        if selected_key not in self._providers:
            msg = f"No provider matches {selected_key}"
            raise RuntimeError(msg)
        return await self._providers[selected_key].async_resolve()

    def sync_resolve(self) -> T:
        selected_key = self._selector()
        if selected_key not in self._providers:
            msg = f"No provider matches {selected_key}"
            raise RuntimeError(msg)
        return self._providers[selected_key].sync_resolve()

    async def __call__(self) -> T:
        return await self.async_resolve()
