import abc
import typing

from that_depends.providers.base import AbstractProvider


T_co = typing.TypeVar("T_co", covariant=True)
P = typing.ParamSpec("P")


class AbstractFactory(AbstractProvider[T_co], abc.ABC):
    @property
    def provider(self) -> typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T_co]]:
        return self.async_resolve

    @property
    def sync_provider(self) -> typing.Callable[[], T_co]:
        return self.sync_resolve


class Factory(AbstractFactory[T_co]):
    __slots__ = "_factory", "_args", "_kwargs", "_override"

    def __init__(self, factory: typing.Callable[P, T_co], *args: P.args, **kwargs: P.kwargs) -> None:
        super().__init__()
        self._factory: typing.Final = factory
        self._args: typing.Final = args
        self._kwargs: typing.Final = kwargs

    async def async_resolve(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        return self._factory(
            *[  # type: ignore[arg-type]
                await x.async_resolve() if isinstance(x, AbstractProvider) else x for x in self._args
            ],
            **{  # type: ignore[arg-type]
                k: await v.async_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()
            },
        )

    def sync_resolve(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        return self._factory(
            *[  # type: ignore[arg-type]
                x.sync_resolve() if isinstance(x, AbstractProvider) else x for x in self._args
            ],
            **{  # type: ignore[arg-type]
                k: v.sync_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()
            },
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
            *[  # type: ignore[arg-type]
                await x.async_resolve() if isinstance(x, AbstractProvider) else x for x in self._args
            ],
            **{  # type: ignore[arg-type]
                k: await v.async_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()
            },
        )

    def sync_resolve(self) -> typing.NoReturn:
        msg = "AsyncFactory cannot be resolved synchronously"
        raise RuntimeError(msg)
