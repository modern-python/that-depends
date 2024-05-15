import typing

from that_depends.providers.base import AbstractProvider


T = typing.TypeVar("T")
P = typing.ParamSpec("P")


class Singleton(AbstractProvider[T]):
    def __init__(self, factory: type[T] | typing.Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> None:
        self._factory = factory
        self._args = args
        self._kwargs = kwargs
        self._override = None
        self._instance: T | None = None

    async def async_resolve(self) -> T:
        if self._override is not None:
            return typing.cast(T, self._override)

        if self._instance is None:
            self._instance = self._factory(
                *[await x.async_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
                **{
                    k: await v.async_resolve() if isinstance(v, AbstractProvider) else v
                    for k, v in self._kwargs.items()
                },
            )
        return self._instance

    def sync_resolve(self) -> T:
        if self._override is not None:
            return typing.cast(T, self._override)

        if self._instance is None:
            self._instance = self._factory(
                *[x.sync_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
                **{k: v.sync_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
            )
        return self._instance

    async def tear_down(self) -> None:
        if self._instance is not None:
            self._instance = None
