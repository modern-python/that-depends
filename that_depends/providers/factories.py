import typing

from that_depends.providers.base import AbstractFactory, AbstractProvider


T = typing.TypeVar("T")
P = typing.ParamSpec("P")


class Factory(AbstractFactory[T]):
    __slots__ = "_factory", "_args", "_kwargs", "_override"

    def __init__(self, factory: type[T] | typing.Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> None:
        super().__init__()
        self._factory: typing.Final = factory
        self._args: typing.Final = args
        self._kwargs: typing.Final = kwargs
        self._override = None

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


class AsyncFactory(AbstractFactory[T]):
    __slots__ = "_factory", "_args", "_kwargs", "_override"

    def __init__(self, factory: typing.Callable[P, typing.Awaitable[T]], *args: P.args, **kwargs: P.kwargs) -> None:
        self._factory: typing.Final = factory
        self._args: typing.Final = args
        self._kwargs: typing.Final = kwargs
        self._override = None

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
