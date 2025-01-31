"""Resource providers."""

import asyncio
import threading
import typing

from typing_extensions import override

from that_depends.providers.base import AbstractProvider


T_co = typing.TypeVar("T_co", covariant=True)
P = typing.ParamSpec("P")


class Singleton(AbstractProvider[T_co]):
    """A provider that creates an instance once and caches it for subsequent injections.

    This provider is safe to use concurrently in both threading and asyncio contexts.
    On the first call to either ``sync_resolve()`` or ``async_resolve()``, the instance
    is created by calling the provided factory. All future calls return the cached instance.

    Example:
        ```python
        def my_factory() -> float:
            return 0.5

        singleton = Singleton(my_factory)
        value1 = singleton.sync_resolve()
        value2 = singleton.sync_resolve()
        assert value1 == value2
        ```

    """

    __slots__ = "_args", "_asyncio_lock", "_factory", "_instance", "_kwargs", "_override", "_threading_lock"

    def __init__(self, factory: typing.Callable[P, T_co], *args: P.args, **kwargs: P.kwargs) -> None:
        """Initialize the Singleton provider.

        Args:
            factory: A callable that produces the instance to be provided.
            *args: Positional arguments to pass to the factory.
            **kwargs: Keyword arguments to pass to the factory.

        """
        super().__init__()
        self._factory: typing.Final = factory
        self._instance: T_co | None = None
        self._asyncio_lock: typing.Final = asyncio.Lock()
        self._threading_lock: typing.Final = threading.Lock()
        self._args: typing.Final[P.args] = args
        self._kwargs: typing.Final[P.kwargs] = kwargs

    @override
    async def async_resolve(self) -> T_co:
        if self._override is not None:
            return typing.cast(T_co, self._override)

        if self._instance is not None:
            return self._instance

        # lock to prevent resolving several times
        async with self._asyncio_lock:
            if self._instance is not None:
                return self._instance

            self._instance = self._factory(
                *[await x.async_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
                **{
                    k: await v.async_resolve() if isinstance(v, AbstractProvider) else v
                    for k, v in self._kwargs.items()
                },
            )
            return self._instance

    @override
    def sync_resolve(self) -> T_co:
        if self._override is not None:
            return typing.cast(T_co, self._override)

        if self._instance is not None:
            return self._instance

        # lock to prevent resolving several times
        with self._threading_lock:
            if self._instance is not None:
                return self._instance

            self._instance = self._factory(
                *[x.sync_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
                **{k: v.sync_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
            )
            return self._instance

    async def tear_down(self) -> None:
        """Reset the cached instance.

        After calling this method, the next resolve call will recreate the instance.
        """
        if self._instance is not None:
            self._instance = None


class AsyncSingleton(AbstractProvider[T_co]):
    """A provider that creates an instance asynchronously and caches it for subsequent injections.

    This provider is safe to use concurrently in asyncio contexts. On the first call
    to ``async_resolve()``, the instance is created by awaiting the provided factory.
    All subsequent calls return the cached instance.

    Example:
        ```python
        async def my_async_factory() -> float:
            return 0.5

        async_singleton = AsyncSingleton(my_async_factory)
        value1 = await async_singleton.async_resolve()
        value2 = await async_singleton.async_resolve()
        assert value1 == value2
        ```

    """

    __slots__ = "_args", "_asyncio_lock", "_factory", "_instance", "_kwargs", "_override"

    def __init__(
        self,
        factory: typing.Callable[P, typing.Awaitable[T_co]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        """Initialize the AsyncSingleton provider.

        Args:
            factory: The asynchronous callable used to create the instance.
            *args: Positional arguments to pass to the factory.
            **kwargs: Keyword arguments to pass to the factory.

        """
        super().__init__()
        self._factory: typing.Final[typing.Callable[P, typing.Awaitable[T_co]]] = factory
        self._instance: T_co | None = None
        self._asyncio_lock: typing.Final = asyncio.Lock()
        self._args: typing.Final[P.args] = args
        self._kwargs: typing.Final[P.kwargs] = kwargs

    @override
    async def async_resolve(self) -> T_co:
        if self._override is not None:
            return typing.cast(T_co, self._override)

        if self._instance is not None:
            return self._instance

        # lock to prevent resolving several times
        async with self._asyncio_lock:
            if self._instance is not None:
                return self._instance

            self._instance = await self._factory(
                *[await x.async_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
                **{
                    k: await v.async_resolve() if isinstance(v, AbstractProvider) else v
                    for k, v in self._kwargs.items()
                },
            )
            return self._instance

    @override
    def sync_resolve(self) -> typing.NoReturn:
        msg = "AsyncSingleton cannot be resolved in an sync context."
        raise RuntimeError(msg)

    async def tear_down(self) -> None:
        """Reset the cached instance.

        After calling this method, the next call to ``async_resolve()`` will recreate the instance.
        """
        if self._instance is not None:
            self._instance = None
