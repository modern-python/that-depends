import typing

from typing_extensions import override

from that_depends.providers.base import AbstractProvider


T_co = typing.TypeVar("T_co", covariant=True)


class List(AbstractProvider[list[T_co]]):
    """Provides multiple resources as a list.

    The `List` provider resolves multiple dependencies into a list.

    Example:
        ```python
        from that_depends import providers

        provider1 = providers.Factory(lambda: 1)
        provider2 = providers.Factory(lambda: 2)

        list_provider = List(provider1, provider2)

        # Synchronous resolution
        resolved_list = list_provider.sync_resolve()
        print(resolved_list)  # Output: [1, 2]

        # Asynchronous resolution
        import asyncio
        resolved_list_async = asyncio.run(list_provider.async_resolve())
        print(resolved_list_async)  # Output: [1, 2]
        ```

    """

    __slots__ = ("_providers",)

    def __init__(self, *providers: AbstractProvider[T_co]) -> None:
        """Create a new List provider instance.

        Args:
            *providers: List of providers to resolve.

        """
        super().__init__()
        self._providers: typing.Final = providers

    @override
    def __getattr__(self, attr_name: str) -> typing.Any:
        msg = f"'{type(self)}' object has no attribute '{attr_name}'"
        raise AttributeError(msg)

    @override
    async def async_resolve(self) -> list[T_co]:
        return [await x.async_resolve() for x in self._providers]

    @override
    def sync_resolve(self) -> list[T_co]:
        return [x.sync_resolve() for x in self._providers]

    @override
    async def __call__(self) -> list[T_co]:
        return await self.async_resolve()


class Dict(AbstractProvider[dict[str, T_co]]):
    """Provides multiple resources as a dictionary.

    The `Dict` provider resolves multiple named dependencies into a dictionary.

    Example:
        ```python
        from that_depends import providers

        provider1 = providers.Factory(lambda: 1)
        provider2 = providers.Factory(lambda: 2)

        dict_provider = Dict(key1=provider1, key2=provider2)

        # Synchronous resolution
        resolved_dict = dict_provider.sync_resolve()
        print(resolved_dict)  # Output: {"key1": 1, "key2": 2}

        # Asynchronous resolution
        import asyncio
        resolved_dict_async = asyncio.run(dict_provider.async_resolve())
        print(resolved_dict_async)  # Output: {"key1": 1, "key2": 2}
        ```

    """

    __slots__ = ("_providers",)

    def __init__(self, **providers: AbstractProvider[T_co]) -> None:
        """Create a new Dict provider instance.

        Args:
            **providers: Dictionary of providers to resolve.

        """
        super().__init__()
        self._providers: typing.Final = providers

    @override
    def __getattr__(self, attr_name: str) -> typing.Any:
        msg = f"'{type(self)}' object has no attribute '{attr_name}'"
        raise AttributeError(msg)

    @override
    async def async_resolve(self) -> dict[str, T_co]:
        return {key: await provider.async_resolve() for key, provider in self._providers.items()}

    @override
    def sync_resolve(self) -> dict[str, T_co]:
        return {key: provider.sync_resolve() for key, provider in self._providers.items()}
