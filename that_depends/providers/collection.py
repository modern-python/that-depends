import typing
from collections.abc import Mapping, Sequence
from types import MappingProxyType

from typing_extensions import override

from that_depends.providers.base import AbstractProvider


T_co = typing.TypeVar("T_co", covariant=True)


class List(AbstractProvider[Sequence[T_co]]):
    """Provides multiple resources as a read-only sequence.

    The `List` provider resolves multiple dependencies into an immutable tuple
    exposed through the `Sequence` interface.

    Example:
        ```python
        from that_depends import providers

        provider1 = providers.Factory(lambda: 1)
        provider2 = providers.Factory(lambda: 2)

        list_provider = List(provider1, provider2)

        # Synchronous resolution
        resolved_list = list_provider.resolve_sync()
        print(tuple(resolved_list))  # Output: (1, 2)

        # Asynchronous resolution
        import asyncio
        resolved_list_async = asyncio.run(list_provider.resolve())
        print(tuple(resolved_list_async))  # Output: (1, 2)
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
        self._register(self._providers)

    @override
    def __getattr__(self, attr_name: str) -> typing.Any:
        msg = f"'{type(self)}' object has no attribute '{attr_name}'"
        raise AttributeError(msg)

    @override
    async def resolve(self) -> Sequence[T_co]:
        resolved = [await x.resolve() for x in self._providers]
        return tuple(resolved)

    @override
    def resolve_sync(self) -> Sequence[T_co]:
        resolved = [x.resolve_sync() for x in self._providers]
        return tuple(resolved)

    @override
    async def __call__(self) -> Sequence[T_co]:
        return await self.resolve()


class Dict(AbstractProvider[Mapping[str, T_co]]):
    """Provides multiple resources as a read-only mapping.

    The `Dict` provider resolves multiple named dependencies into a read-only mapping.

    Example:
        ```python
        from that_depends import providers

        provider1 = providers.Factory(lambda: 1)
        provider2 = providers.Factory(lambda: 2)

        dict_provider = Dict(key1=provider1, key2=provider2)

        # Synchronous resolution
        resolved_dict = dict_provider.resolve_sync()
        print(dict(resolved_dict))  # Output: {"key1": 1, "key2": 2}

        # Asynchronous resolution
        import asyncio
        resolved_dict_async = asyncio.run(dict_provider.resolve())
        print(dict(resolved_dict_async))  # Output: {"key1": 1, "key2": 2}
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
        self._register(self._providers.values())

    @override
    def __getattr__(self, attr_name: str) -> typing.Any:
        msg = f"'{type(self)}' object has no attribute '{attr_name}'"
        raise AttributeError(msg)

    @override
    async def resolve(self) -> Mapping[str, T_co]:
        return MappingProxyType({key: await provider.resolve() for key, provider in self._providers.items()})

    @override
    def resolve_sync(self) -> Mapping[str, T_co]:
        return MappingProxyType({key: provider.resolve_sync() for key, provider in self._providers.items()})
