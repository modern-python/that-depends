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

    def __init__(
        self, selector: typing.Callable[[], str] | AbstractProvider[str] | str, **providers: AbstractProvider[T_co]
    ) -> None:
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
        self._selector: typing.Final[typing.Callable[[], str] | AbstractProvider[str] | str] = selector
        self._providers: typing.Final = providers

    @override
    async def resolve(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        if isinstance(self._selector, AbstractProvider):
            selected_key = await self._selector.resolve()
        else:
            selected_key = self._get_selected_key()

        self._validate_key(selected_key)

        return await self._providers[selected_key].resolve()

    @override
    def resolve_sync(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        if isinstance(self._selector, AbstractProvider):
            selected_key = self._selector.resolve_sync()
        else:
            selected_key = self._get_selected_key()

        self._validate_key(selected_key)

        return self._providers[selected_key].resolve_sync()

    def _get_selected_key(self) -> str:
        if callable(self._selector):
            selected_key = self._selector()
        elif isinstance(self._selector, str):
            selected_key = self._selector
        else:
            msg = f"Invalid selector type: {type(self._selector)}, expected str, or a provider/callable returning str"
            raise TypeError(msg)
        return typing.cast(str, selected_key)

    def _validate_key(self, key: str) -> None:
        if key not in self._providers:
            msg = f"Key '{key}' not found in providers"
            raise KeyError(msg)
