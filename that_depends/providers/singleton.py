"""Resource providers."""

import asyncio
import threading
import typing

from typing_extensions import override

from that_depends.providers.base import AbstractProvider
from that_depends.providers.mixin import SupportsTeardown


T_co = typing.TypeVar("T_co", covariant=True)
P = typing.ParamSpec("P")


class Singleton(SupportsTeardown, AbstractProvider[T_co]):
    """A provider that creates an instance once and caches it for subsequent injections.

    This provider is safe to use concurrently in both threading and asyncio contexts.
    On the first call to either ``resolve_sync()`` or ``resolve()``, the instance
    is created by calling the provided factory. All future calls return the cached instance.

    Example:
        ```python
        def my_factory() -> float:
            return 0.5

        singleton = Singleton(my_factory)
        value1 = singleton.resolve_sync()
        value2 = singleton.resolve_sync()
        assert value1 == value2
        ```

    """

    __slots__ = "_args", "_asyncio_lock", "_factory", "_instance", "_kwargs", "_override", "_threading_lock"

    def __init__(self, factory: typing.Callable[P, T_co], *args: typing.Any, **kwargs: typing.Any) -> None:  # noqa: ANN401
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
        self._args: typing.Final = args
        self._kwargs: typing.Final = kwargs

    def _register_arguments(self) -> None:
        self._register(self._args)
        self._register(self._kwargs.values())

    def _deregister_arguments(self) -> None:
        self._deregister(self._args)
        self._deregister(self._kwargs.values())

    @override
    async def resolve(self, **kwargs: typing.Any) -> T_co:
        if self._override is not None:
            self._register_arguments()
            return typing.cast(T_co, self._override)

        # lock to prevent resolving several times
        async with self._asyncio_lock:
            if self._instance is not None:
                return self._instance
            self._register_arguments()
            self._instance = self._factory(
                *[await x.resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
                **{k: await v.resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
            )
            return self._instance

    @override
    def resolve_sync(self, **kwargs: typing.Any) -> T_co:
        if self._override is not None:
            self._register_arguments()
            return typing.cast(T_co, self._override)

        # lock to prevent resolving several times
        with self._threading_lock:
            if self._instance is not None:
                return self._instance
            self._register_arguments()
            self._instance = self._factory(
                *[x.resolve_sync() if isinstance(x, AbstractProvider) else x for x in self._args],
                **{
                    **kwargs,
                    **{k: v.resolve_sync() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
                },
            )
            return self._instance

    @override
    async def tear_down(self, propagate: bool = True) -> None:
        """Reset the cached instance.

        After calling this method, the next resolve call will recreate the instance.
        """
        if self._instance is not None:
            self._instance = None
        self._deregister_arguments()
        if propagate:
            await self._tear_down_children()

    @override
    def tear_down_sync(self, propagate: bool = True, raise_on_async: bool = True) -> None:
        """Reset the cached instance.

        After calling this method, the next resolve call will recreate the instance.
        """
        if self._instance is not None:
            self._instance = None
        self._deregister_arguments()
        if propagate:
            self._tear_down_children_sync(propagate=propagate, raise_on_async=raise_on_async)


class AsyncSingleton(SupportsTeardown, AbstractProvider[T_co]):
    """A provider that creates an instance asynchronously and caches it for subsequent injections.

    This provider is safe to use concurrently in asyncio contexts. On the first call
    to ``resolve()``, the instance is created by awaiting the provided factory.
    All subsequent calls return the cached instance.

    Example:
        ```python
        async def my_async_factory() -> float:
            return 0.5

        async_singleton = AsyncSingleton(my_async_factory)
        value1 = await async_singleton.resolve()
        value2 = await async_singleton.resolve()
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
        self._args: typing.Final = args
        self._kwargs: typing.Final = kwargs

    def _register_arguments(self) -> None:
        self._register(self._args)
        self._register(self._kwargs.values())

    def _deregister_arguments(self) -> None:
        self._deregister(self._args)
        self._deregister(self._kwargs.values())

    @override
    async def resolve(self, **kwargs: typing.Any) -> T_co:
        if self._override is not None:
            return typing.cast(T_co, self._override)

        # lock to prevent resolving several times
        async with self._asyncio_lock:
            if self._instance is not None:
                return self._instance

            self._register_arguments()

            self._instance = await self._factory(
                *[await x.resolve() if isinstance(x, AbstractProvider) else x for x in self._args],  # type: ignore[arg-type]
                **{  # type: ignore[arg-type]
                    k: await v.resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()
                },
            )
            return self._instance

    @override
    def resolve_sync(self, **kwargs: typing.Any) -> typing.NoReturn:
        msg = "AsyncSingleton cannot be resolved in an sync context."
        raise RuntimeError(msg)

    @override
    async def tear_down(self, propagate: bool = True) -> None:
        """Reset the cached instance.

        After calling this method, the next call to ``resolve()`` will recreate the instance.
        """
        if self._instance is not None:
            self._instance = None
        self._deregister_arguments()
        if propagate:
            await self._tear_down_children()

    @override
    def tear_down_sync(self, propagate: bool = True, raise_on_async: bool = True) -> None:
        """Reset the cached instance.

        After calling this method, the next call to ``resolve_sync()`` will recreate the instance.
        """
        if self._instance is not None:
            self._instance = None
        self._deregister_arguments()
        if propagate:
            self._tear_down_children_sync(propagate=propagate, raise_on_async=raise_on_async)
