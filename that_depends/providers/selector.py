import typing

from that_depends.providers.base import AbstractProvider


T = typing.TypeVar("T")


class Selector(AbstractProvider[T]):
    __slots__ = "_selector", "_providers", "_override"

    def __init__(self, selector: typing.Callable[[], str], **providers: AbstractProvider[T]) -> None:
        self._selector: typing.Final = selector
        self._providers: typing.Final = providers
        self._override = None

    async def async_resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        selected_key: typing.Final = self._selector()
        if selected_key not in self._providers:
            msg = f"No provider matches {selected_key}"
            raise RuntimeError(msg)
        return await self._providers[selected_key].async_resolve()

    def sync_resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        selected_key: typing.Final = self._selector()
        if selected_key not in self._providers:
            msg = f"No provider matches {selected_key}"
            raise RuntimeError(msg)
        return self._providers[selected_key].sync_resolve()
