import typing
from collections.abc import Collection
from itertools import chain

from that_depends.providers.base import AbstractFactory, AbstractProvider


T = typing.TypeVar("T")
P = typing.ParamSpec("P")


class Factory(AbstractFactory[T]):
    __slots__ = "_factory", "_args", "_kwargs", "_override", "_dependencies"

    def __init__(self, factory: type[T] | typing.Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> None:
        self._factory = factory
        self._args = args
        self._kwargs = kwargs
        self._override = None
        self._dependencies = [d for d in chain(args, kwargs.values()) if isinstance(d, AbstractProvider)]

    async def async_resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        return self._factory(
            *[await x.async_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
            **{k: await v.async_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
        )

    def sync_resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        return self._factory(
            *[x.sync_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
            **{k: v.sync_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
        )

    @property
    def dependencies(self) -> Collection[AbstractProvider[typing.Any]]:
        return self._dependencies


class AsyncFactory(AbstractFactory[T]):
    __slots__ = "_factory", "_args", "_kwargs", "_override", "_dependencies"

    def __init__(self, factory: typing.Callable[P, typing.Awaitable[T]], *args: P.args, **kwargs: P.kwargs) -> None:
        self._factory = factory
        self._args = args
        self._kwargs = kwargs
        self._override = None
        self._dependencies = [d for d in chain(args, kwargs.values()) if isinstance(d, AbstractProvider)]

    async def async_resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        return await self._factory(
            *[await x.async_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
            **{k: await v.async_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
        )

    def sync_resolve(self) -> typing.NoReturn:
        msg = "AsyncFactory cannot be resolved synchronously"
        raise RuntimeError(msg)

    @property
    def dependencies(self) -> Collection[AbstractProvider[typing.Any]]:
        return self._dependencies
