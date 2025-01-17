"""Selection based providers."""

import typing

from typing_extensions import override

from that_depends.providers.base import AbstractProvider


T_co = typing.TypeVar("T_co", covariant=True)


class Selector(AbstractProvider[T_co]):
    """Chooses a provider based on a key returned by a selector function.

    This class allows you to dynamically select and resolve one of several
    named providers at runtime. The provider key is determined by a
    user-supplied selector function.

    Examples:
        ```python
        def environment_selector():
            return "local"

        selector_instance = Selector(
            environment_selector,
            local=LocalStorageProvider(),
            remote=RemoteStorageProvider(),
        )

        # Synchronously resolve the selected provider
        service = selector_instance.sync_resolve()
        ```

    """

    __slots__ = "_override", "_providers", "_selector"

    def __init__(self, selector: typing.Callable[[], str], **providers: AbstractProvider[T_co]) -> None:
        """Initialize a new Selector instance.

        Args:
            selector (Callable[[], str]): A function that returns the key
                of the provider to use.
            **providers (AbstractProvider[T_co]): The named providers from
                which one will be selected based on the `selector`.

        Examples:
            ```python
            def my_selector():
                return "remote"

            my_selector_instance = Selector(
                my_selector,
                local=LocalStorageProvider(),
                remote=RemoteStorageProvider(),
            )

            # The "remote" provider will be selected
            selected_service = my_selector_instance.sync_resolve()
            ```

        """
        super().__init__()
        self._selector: typing.Final = selector
        self._providers: typing.Final = providers

    @override
    async def async_resolve(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        selected_key: typing.Final = self._selector()
        if selected_key not in self._providers:
            msg = f"No provider matches {selected_key}"
            raise RuntimeError(msg)
        return await self._providers[selected_key].async_resolve()

    @override
    def sync_resolve(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        selected_key: typing.Final = self._selector()
        if selected_key not in self._providers:
            msg = f"No provider matches {selected_key}"
            raise RuntimeError(msg)
        return self._providers[selected_key].sync_resolve()
