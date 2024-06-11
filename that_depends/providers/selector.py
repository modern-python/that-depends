import typing

from that_depends.providers.base import AbstractProvider


T = typing.TypeVar("T")


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
