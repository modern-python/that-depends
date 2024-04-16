import typing

from that_depends.providers.base import AbstractProvider


T = typing.TypeVar("T")
P = typing.ParamSpec("P")


class Factory(AbstractProvider[T]):
    def __init__(self, factory: type[T] | typing.Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> None:
        self._factory = factory
        self._args = args
        self._kwargs = kwargs
        self._override = None

    async def resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        return self._factory(
            *[await x() if isinstance(x, AbstractProvider) else x for x in self._args],
            **{k: await v() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
        )


class AsyncFactory(AbstractProvider[T]):
    def __init__(self, factory: typing.Callable[P, typing.Awaitable[T]], *args: P.args, **kwargs: P.kwargs) -> None:
        self._factory = factory
        self._args = args
        self._kwargs = kwargs
        self._override = None

    async def resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        return await self._factory(
            *[await x() if isinstance(x, AbstractProvider) else x for x in self._args],
            **{k: await v() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
        )
