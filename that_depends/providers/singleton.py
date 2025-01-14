"""Resource providers."""

import asyncio
import threading
import typing
from typing import override

from that_depends.providers.base import AbstractProvider


T_co = typing.TypeVar("T_co", covariant=True)
P = typing.ParamSpec("P")


class Singleton(AbstractProvider[T_co]):
    """Provider that creates an instance and caches it."""

    __slots__ = "_args", "_asyncio_lock", "_factory", "_instance", "_kwargs", "_override", "_threading_lock"

    def __init__(self, factory: typing.Callable[P, T_co], *args: P.args, **kwargs: P.kwargs) -> None:
        """Initialize the provider."""
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
        """Tear down the instance."""
        if self._instance is not None:
            self._instance = None


class AsyncSingleton(AbstractProvider[T_co]):
    """Provider that creates an instance asynchronously and caches it."""

    __slots__ = "_args", "_asyncio_lock", "_factory", "_instance", "_kwargs", "_override"

    def __init__(self, factory: typing.Callable[P, typing.Awaitable[T_co]], *args: P.args, **kwargs: P.kwargs) -> None:
        """Initialize the provider.

        Args:
            factory: method that creates an instance to be provided.
            *args: arguments to pass to the created instance.
            **kwargs: keyword arguments to pass to the created instance.

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
        """Tear down the instance."""
        if self._instance is not None:
            self._instance = None
