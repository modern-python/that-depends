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
        self._args: typing.Final = args
        self._kwargs: typing.Final = kwargs
        self._instance: T_co | None = None
        self._asyncio_lock: typing.Final = asyncio.Lock()
        self._threading_lock: typing.Final = threading.Lock()

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
                *[  # type: ignore[arg-type]
                    await x.async_resolve() if isinstance(x, AbstractProvider) else x for x in self._args
                ],
                **{  # type: ignore[arg-type]
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
                *[  # type: ignore[arg-type]
                    x.sync_resolve() if isinstance(x, AbstractProvider) else x for x in self._args
                ],
                **{  # type: ignore[arg-type]
                    k: v.sync_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()
                },
            )
            return self._instance

    async def tear_down(self) -> None:
        """Reset the cached instance.

        After calling this method, the next resolve call will recreate the instance.
        """
        if self._instance is not None:
            self._instance = None


class ThreadLocalSingleton(AbstractProvider[T_co]):
    """Creates a new instance for each thread using a thread-local store.

    This provider ensures that each thread gets its own instance, which is
    created via the specified factory function. Once created, the instance is
    cached for future injections within the same thread.

    Example:
        ```python
        def factory():
            return random.randint(1, 100)

        singleton = ThreadLocalSingleton(factory)

        # Same thread, same instance
        instance1 = singleton.sync_resolve()
        instance2 = singleton.sync_resolve()

        def thread_task():
            return singleton.sync_resolve()

        threads = [threading.Thread(target=thread_task) for i in range(10)]
        for thread in threads:
            thread.start() # Each thread will get a different instance
        ```

    """

    def __init__(self, factory: typing.Callable[P, T_co], *args: P.args, **kwargs: P.kwargs) -> None:
        """Initialize the ThreadLocalSingleton provider.

        Args:
            factory: A callable that returns a new instance of the dependency.
            *args: Positional arguments to pass to the factory.
            **kwargs: Keyword arguments to pass to the factory.

        """
        super().__init__()
        self._factory: typing.Final = factory
        self._args: typing.Final = args
        self._kwargs: typing.Final = kwargs
        self._thread_local = threading.local()

    @property
    def _instance(self) -> T_co | None:
        return getattr(self._thread_local, "instance", None)

    @_instance.setter
    def _instance(self, value: T_co | None) -> None:
        self._thread_local.instance = value

    @override
    async def async_resolve(self) -> T_co:
        msg = "ThreadLocalSingleton cannot be resolved in an async context."
        raise NotImplementedError(msg)

    @override
    def sync_resolve(self) -> T_co:
        if self._override is not None:
            return typing.cast(T_co, self._override)

        if self._instance is not None:
            return self._instance

        self._instance = self._factory(
            *[x.sync_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],  # type: ignore[arg-type]
            **{k: v.sync_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},  # type: ignore[arg-type]
        )
        return self._instance

    def tear_down(self) -> None:
        """Reset the thread-local instance.

        After calling this method, subsequent calls to `sync_resolve` on the
        same thread will produce a new instance.
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
        self._args: typing.Final[P.args] = args
        self._kwargs: typing.Final[P.kwargs] = kwargs
        self._instance: T_co | None = None
        self._asyncio_lock: typing.Final = asyncio.Lock()

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
