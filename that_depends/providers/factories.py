import typing

from that_depends.providers.base import AbstractFactory, AbstractProvider


T_co = typing.TypeVar("T_co", covariant=True)
P = typing.ParamSpec("P")


class Factory(AbstractFactory[T_co]):
    __slots__ = "_factory", "_args", "_kwargs", "_override"

    def __init__(self, factory: type[T_co] | typing.Callable[P, T_co], *args: P.args, **kwargs: P.kwargs) -> None:
        super().__init__()
        self._factory: typing.Final = factory
        self._args: typing.Final = args
        self._kwargs: typing.Final = kwargs

    async def async_resolve(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        return self._factory(
            *[await x.async_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
            **{k: await v.async_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
        )

    def sync_resolve(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        return self._factory(
            *[x.sync_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
            **{k: v.sync_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
        )


class AsyncFactory(AbstractFactory[T_co]):
    __slots__ = "_factory", "_args", "_kwargs", "_override"

    def __init__(self, factory: typing.Callable[P, typing.Awaitable[T_co]], *args: P.args, **kwargs: P.kwargs) -> None:
        super().__init__()
        self._factory: typing.Final = factory
        self._args: typing.Final = args
        self._kwargs: typing.Final = kwargs

    async def async_resolve(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        return await self._factory(
            *[await x.async_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
            **{k: await v.async_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
        )

    def sync_resolve(self) -> typing.NoReturn:
        msg = "AsyncFactory cannot be resolved synchronously"
        raise RuntimeError(msg)
